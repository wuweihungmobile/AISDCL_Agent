package com.aisdlc.console.adapter.in.web;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.classic.spi.IThrowableProxy;
import ch.qos.logback.core.read.ListAppender;
import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.SseProbe;
import com.aisdlc.console.support.SseProbe.Frame;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import tools.jackson.databind.JsonNode;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 前端 SSE 兩條端點（契約 §2；E2E-12；API-SSE-01～03）——對<b>真的 HTTP 伺服器</b>以串流讀取，斷言解析後的欄位：
 * 認證（Bearer 與 {@code ?access_token=}）、框架格式、id 規則與 {@code Last-Event-ID} 重播、{@code /metrics} 的收斂快照、
 * 終態與 204、keep-alive、Bridge 暫時不可達的連線告警，以及串流正常結束後的日誌沒有 {@code AccessDeniedException}、
 * 任何日誌都不含 {@code access_token}。
 */
class StreamApiIT extends AbstractExecutionIT {

    private ListAppender<ILoggingEvent> logs;
    private Logger root;
    private final List<SseProbe> probes = new ArrayList<>();

    @BeforeEach
    void captureLogs() {
        root = (Logger) LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME);
        logs = new ListAppender<>();
        logs.start();
        root.addAppender(logs);
    }

    @AfterEach
    void releaseLogsAndStreams() {
        root.detachAppender(logs);
        logs.stop();
        probes.forEach(SseProbe::close);
        probes.clear();
    }

    private SseProbe open(String path, String token) {
        SseProbe probe = SseProbe.open(baseUrl() + path, token == null ? Map.of() : Map.of("Authorization", "Bearer " + token));
        probes.add(probe);
        return probe;
    }

    private SseProbe open(String path, Map<String, String> headers) {
        SseProbe probe = SseProbe.open(baseUrl() + path, headers);
        probes.add(probe);
        return probe;
    }

    private static String logsPath(String run) {
        return "/api/v1/stream/executions/" + run + "/logs";
    }

    private static String metricsPath(String run) {
        return "/api/v1/stream/executions/" + run + "/metrics";
    }

    /** 迷你 Bridge 事件中，{@code /logs} 會對映出框架的那幾種（status／step／log／alert）的 seq。 */
    private static List<String> expectedLogIds(List<Map<String, Object>> events) {
        return events.stream().filter(e -> List.of("status", "step", "log", "alert").contains(e.get("event")))
                .map(e -> String.valueOf(e.get("seq"))).toList();
    }

    private String completedRun(String name) {
        Fixture f = prjA(name, 4);
        String run = startRun(f.projectId());
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        assertThat(consumers.awaitIdle(Duration.ofSeconds(5))).isTrue();
        return run;
    }

    // ── 認證 ────────────────────────────────────────────────────────────────────────

    @Test
    void bothTheBearerHeaderAndTheAccessTokenQueryParameterAreAccepted() {
        String run = completedRun("auth");
        SseProbe viaHeader = open(logsPath(run), viewer());
        assertThat(viaHeader.status()).isEqualTo(200);
        SseProbe viaQuery = open(logsPath(run) + "?access_token=" + viewer(), (String) null);
        assertThat(viaQuery.status()).isEqualTo(200);
        assertThat(viaQuery.awaitEnd(Duration.ofSeconds(10))).isTrue();
        assertThat(viaHeader.awaitEnd(Duration.ofSeconds(10))).isTrue();
        assertThat(viaQuery.eventNames()).isEqualTo(viaHeader.eventNames());
    }

    @Test
    void theHeaderWinsOverTheQueryParameterAndOnlyAccessTokensAreAccepted() {
        String run = completedRun("auth-priority");
        Map<String, String> badHeader = Map.of("Authorization", "Bearer not-a-token");
        SseProbe headerInvalid = open(logsPath(run) + "?access_token=" + viewer(), badHeader);
        assertThat(headerInvalid.status()).as("標頭優先：標頭無效不退回 query").isEqualTo(401);
        assertThat(open(logsPath(run) + "?access_token=garbage", viewer()).status()).as("標頭有效時 query 被忽略")
                .isEqualTo(200);

        String refresh = api.post(null, "/api/v1/auth/login", Map.of("username", "viewer", "password", "Viewer#Dev2026"))
                .read("$.data.refreshToken");
        SseProbe refreshQuery = open(logsPath(run) + "?access_token=" + refresh, (String) null);
        assertThat(refreshQuery.status()).as("refresh token 一律 401").isEqualTo(401);
        assertThat(refreshQuery.rawBody()).contains("TOKEN_INVALID");
        SseProbe refreshHeader = open(logsPath(run), refresh);
        assertThat(refreshHeader.status()).isEqualTo(401);
    }

    @Test
    void anAnonymousRequestAndAnInvalidQueryTokenGetA401JsonBeforeTheStreamStarts() {
        String run = completedRun("auth-401");
        SseProbe anonymous = open(logsPath(run), (String) null);
        assertThat(anonymous.status()).isEqualTo(401);
        assertThat(anonymous.header("Content-Type")).startsWith("application/json");
        assertThat(anonymous.rawBody()).contains("\"UNAUTHENTICATED\"");
        SseProbe invalid = open(metricsPath(run) + "?access_token=garbage", (String) null);
        assertThat(invalid.status()).isEqualTo(401);
        assertThat(invalid.rawBody()).contains("TOKEN_INVALID");
    }

    @Test
    void aCrossOriginStreamIsReadableByTheConfiguredFrontendOriginOnly() {
        String run = completedRun("cors");
        SseProbe allowed = open(logsPath(run), Map.of("Authorization", "Bearer " + viewer(),
                "Origin", "http://localhost:3000"));
        assertThat(allowed.status()).isEqualTo(200);
        assertThat(allowed.header("Access-Control-Allow-Origin")).isEqualTo("http://localhost:3000");
        assertThat(allowed.header("Access-Control-Expose-Headers")).as("串流回應的追蹤碼也要讀得到")
                .contains("X-Trace-Id", "X-Follow-Up-Run-Id", "Retry-After", "Content-Disposition");
        assertThat(allowed.header("Content-Type")).startsWith("text/event-stream");
        assertThat(allowed.awaitEnd(Duration.ofSeconds(10))).isTrue();
        assertThat(allowed.events()).as("跨來源也收得到事件").isNotEmpty();

        SseProbe foreign = open(logsPath(run), Map.of("Authorization", "Bearer " + viewer(),
                "Origin", "https://evil.example"));
        assertThat(foreign.status()).as("沒列在 allowed-origins 的來源直接被拒，不開串流").isEqualTo(403);
        assertThat(foreign.header("Access-Control-Allow-Origin")).isNull();
    }

    @Test
    void theQueryTokenIsOnlyHonouredOnTheStreamPathsNotOnOrdinaryEndpoints() {
        String run = completedRun("query-scope");
        Resp ordinary = api.get(null, "/api/v1/executions/" + run + "?access_token=" + viewer());
        assertThat(ordinary.status()).isEqualTo(401);
        assertThat(api.get(viewer(), "/api/v1/executions/" + run + "?access_token=garbage").status()).isEqualTo(200);
    }

    @Test
    void anUnknownRunIs404JsonAndAMalformedIdIs400AndEveryRoleMayRead() {
        String missing = UUID.randomUUID().toString();
        SseProbe unknown = open(logsPath(missing), viewer());
        assertThat(unknown.status()).isEqualTo(404);
        assertThat(unknown.header("Content-Type")).startsWith("application/json");
        assertThat(unknown.rawBody()).contains("執行批次不存在或已刪除：" + missing);
        assertThat(open(metricsPath(missing), operator()).status()).isEqualTo(404);
        assertThat(open("/api/v1/stream/executions/not-a-uuid/logs", viewer()).status()).isEqualTo(400);
        String run = completedRun("roles");
        for (String token : List.of(viewer(), operator(), admin())) {
            assertThat(open(logsPath(run), token).status()).isEqualTo(200);
        }
    }

    // ── 框架格式 ────────────────────────────────────────────────────────────────────

    @Test
    void theStreamStartsWithRetry3000ThenIdEventDataFramesWithCompactUtf8JsonAndTheContractHeaders() {
        String run = completedRun("framing");
        SseProbe probe = open(logsPath(run), viewer());
        assertThat(probe.header("Content-Type")).isEqualToIgnoringCase("text/event-stream;charset=UTF-8");
        assertThat(probe.header("Cache-Control")).isEqualTo("no-cache, no-store");
        assertThat(probe.header("X-Accel-Buffering")).isEqualTo("no");
        assertThat(probe.awaitEnd(Duration.ofSeconds(10))).isTrue();
        Frame first = probe.frames().get(0);
        assertThat(first.retry()).as("第一個框架是 retry").isEqualTo(3000);
        assertThat(first.event()).isNull();
        for (Frame frame : probe.events()) {
            assertThat(frame.id()).isNotBlank();
            assertThat(frame.event()).isIn("log", "status-change", "review-request", "alert");
            assertThat(frame.data()).doesNotContain("\n");
            JsonNode json = frame.json();
            assertThat(json.has("seq")).isTrue();
            assertThat(json.has("ts")).isTrue();
            assertThat(frame.data()).as("不輸出 null").doesNotContain(":null");
        }
        Frame started = probe.events("log").get(0);
        assertThat(started.json().get("source").asString()).isEqualTo("STEP");
        assertThat(started.json().get("message").asString()).as("中文逐字、不跳脫").isEqualTo("開始：初始化（G1-T1，第 1 次）");
        assertThat(started.data()).contains("開始：初始化");
        assertThat(started.json().get("stepId").asString()).isEqualTo("G1-T1");
        assertThat(started.json().get("stepNumber").asInt()).isEqualTo(1);
        assertThat(started.json().get("stepStatus").asString()).isEqualTo("STARTED");
        assertThat(started.json().get("attempt").asInt()).isEqualTo(1);
        assertThat(started.json().get("level").asString()).isEqualTo("INFO");
        Frame last = probe.events().get(probe.events().size() - 1);
        assertThat(last.event()).isEqualTo("status-change");
        assertThat(last.json().get("runStatus").asString()).isEqualTo("COMPLETED");
        assertThat(last.json().get("bridgeStatus").asString()).isEqualTo("COMPLETED");
        assertThat(last.json().get("reason").asString()).isEqualTo("引擎正常結束");
    }

    // ── /logs：重播、id 規則、終態 ───────────────────────────────────────────────────

    @Test
    void connectingToAFinishedRunReplaysEveryEventWithTheBridgeSeqAsIdThenClosesTheStream() {
        String run = completedRun("replay-all");
        SseProbe probe = open(logsPath(run), viewer());
        assertThat(probe.awaitEnd(Duration.ofSeconds(10))).as("終態重播完就關閉").isTrue();
        assertThat(probe.events().stream().map(Frame::id).toList()).isEqualTo(expectedLogIds(mini(run).events()));
        assertThat(SseProbe.strictlyIncreasing(probe.events())).isTrue();
        assertThat(probe.eventNames()).startsWith("status-change", "status-change", "log").endsWith("status-change");
        assertThat(probe.events("status-change").stream().map(f -> f.json().get("runStatus").asString()).toList())
                .containsExactly("INITIALIZING", "RUNNING", "COMPLETED");
        assertThat(probe.events("log").stream().map(f -> f.json().get("stepStatus").asString()).toList())
                .containsExactly("STARTED", "COMPLETED", "STARTED", "COMPLETED", "STARTED", "COMPLETED");
    }

    @Test
    void theCompletedStepLogCarriesTheTokensAttributedToTheTaskAndStartedOnesDoNot() {
        String run = completedRun("replay-tokens");
        SseProbe probe = open(logsPath(run), viewer());
        assertThat(probe.awaitEnd(Duration.ofSeconds(10))).isTrue();
        for (Frame log : probe.events("log")) {
            if ("COMPLETED".equals(log.json().get("stepStatus").asString())) {
                assertThat(log.json().get("tokensUsed").asLong()).isEqualTo(1240L);
                assertThat(log.json().get("message").asString()).endsWith(" Token: 1240");
            } else {
                assertThat(log.json().has("tokensUsed")).isFalse();
            }
        }
    }

    @Test
    void lastEventIdReplaysOnlyStrictlyLaterEventsAndAnEmptyReplayOfATerminalRunIs204() {
        String run = completedRun("replay-slice");
        List<String> all = expectedLogIds(mini(run).events());
        String pivot = all.get(all.size() / 2);
        SseProbe slice = open(logsPath(run), Map.of("Authorization", "Bearer " + viewer(), "Last-Event-ID", pivot));
        assertThat(slice.awaitEnd(Duration.ofSeconds(10))).isTrue();
        assertThat(slice.events().stream().map(Frame::id).toList()).isEqualTo(all.subList(all.size() / 2 + 1, all.size()));

        String lastId = all.get(all.size() - 1);
        SseProbe empty = open(logsPath(run), Map.of("Authorization", "Bearer " + viewer(), "Last-Event-ID", lastId));
        assertThat(empty.status()).as("重播集合為空且 run 已終態 → 204（EventSource 不再重連）").isEqualTo(204);
        SseProbe beyond = open(logsPath(run), Map.of("Authorization", "Bearer " + viewer(), "Last-Event-ID", "99999.7"));
        assertThat(beyond.status()).isEqualTo(204);
    }

    @Test
    void aMalformedLastEventIdIsTreatedAsAbsentAndNeverA400() {
        String run = completedRun("bad-last-id");
        for (String bad : List.of("abc", "1.2.3", "-4", "7.", ".7", "1,2")) {
            SseProbe probe = open(logsPath(run), Map.of("Authorization", "Bearer " + viewer(), "Last-Event-ID", bad));
            assertThat(probe.status()).as(bad).isEqualTo(200);
            assertThat(probe.awaitEnd(Duration.ofSeconds(10))).isTrue();
            assertThat(probe.events().stream().map(Frame::id).toList()).as(bad)
                    .isEqualTo(expectedLogIds(mini(run).events()));
        }
    }

    @Test
    void tailLimitsTheReplayWhenThereIsNoLastEventIdAndTailZeroOnAFinishedRunIs204() {
        String run = completedRun("tail");
        List<String> all = expectedLogIds(mini(run).events());
        SseProbe two = open(logsPath(run) + "?tail=2", viewer());
        assertThat(two.awaitEnd(Duration.ofSeconds(10))).isTrue();
        assertThat(two.events().stream().map(Frame::id).toList()).isEqualTo(all.subList(all.size() - 2, all.size()));
        assertThat(open(logsPath(run) + "?tail=0", viewer()).status()).isEqualTo(204);
        SseProbe huge = open(logsPath(run) + "?tail=999999", viewer());
        assertThat(huge.awaitEnd(Duration.ofSeconds(10))).isTrue();
        assertThat(huge.events()).hasSize(all.size());
    }

    // ── /logs：即時、重連去重、Console 自產事件 ───────────────────────────────────────

    @Test
    void aLiveSubscriberSeesEventsAsTheyHappenAndTheStreamEndsWithTheTerminalStatus() {
        Fixture f = prjA("live", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        SseProbe probe = open(logsPath(run) + "?tail=0", viewer());
        assertThat(probe.events()).as("tail=0 只收之後的新事件").isEmpty();

        mini(run).release(1);
        Frame completed = probe.await(f2 -> f2.isEvent() && "log".equals(f2.event())
                && "COMPLETED".equals(f2.json().get("stepStatus").asString()), Duration.ofSeconds(10));
        assertThat(completed).isNotNull();
        mini(run).release(5);
        assertThat(probe.awaitEnd(Duration.ofSeconds(15))).isTrue();
        assertThat(SseProbe.strictlyIncreasing(probe.events())).isTrue();
        Frame last = probe.events().get(probe.events().size() - 1);
        assertThat(last.event()).isEqualTo("status-change");
        assertThat(last.json().get("runStatus").asString()).isEqualTo("COMPLETED");
    }

    @Test
    void aReconnectWithTheLastSeenIdMissesNothingAndRepeatsNothing() {
        Fixture f = prjA("reconnect-ids", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        SseProbe first = open(logsPath(run), viewer());
        mini(run).release(1);
        Frame seen = first.await(fr -> fr.isEvent() && "log".equals(fr.event())
                && "COMPLETED".equals(fr.json().get("stepStatus").asString()), Duration.ofSeconds(10));
        assertThat(seen).isNotNull();
        first.close();
        mini(run).release(5);
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();

        SseProbe second = open(logsPath(run), Map.of("Authorization", "Bearer " + viewer(), "Last-Event-ID", seen.id()));
        assertThat(second.awaitEnd(Duration.ofSeconds(10))).isTrue();
        List<String> combined = new ArrayList<>(first.events().stream().map(Frame::id).takeWhile(id -> !id.equals(seen.id()))
                .toList());
        combined.add(seen.id());
        combined.addAll(second.events().stream().map(Frame::id).toList());
        assertThat(combined).as("兩段合起來＝完整序列，無缺口無重複").isEqualTo(expectedLogIds(mini(run).events()));
    }

    @Test
    void severalSubscribersEachReceiveTheSameCompleteSequence() {
        Fixture f = prjA("fanout", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        SseProbe a = open(logsPath(run), viewer());
        SseProbe b = open(logsPath(run), operator());
        SseProbe c = open(logsPath(run) + "?access_token=" + admin(), (String) null);
        mini(run).release(5);
        for (SseProbe probe : List.of(a, b, c)) {
            assertThat(probe.awaitEnd(Duration.ofSeconds(15))).isTrue();
            assertThat(probe.events().stream().map(Frame::id).toList()).isEqualTo(expectedLogIds(mini(run).events()));
        }
    }

    @Test
    void aGateReviewRequestIsPushedAfterItsStatusChangeWithAnAnchoredSubSequenceAndTheFullReview() {
        Fixture f = prjA("review-frame", 1);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        SseProbe probe = open(logsPath(run), viewer());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "PAUSING".equals(mini(run).status()))).isTrue();
        mini(run).release(1);

        Frame review = probe.awaitEvent("review-request", Duration.ofSeconds(15));
        assertThat(review).isNotNull();
        JsonNode data = review.json();
        String paused = probe.events("status-change").stream().filter(s -> "PAUSED".equals(s.json().get("runStatus").asString()))
                .map(Frame::id).findFirst().orElseThrow();
        assertThat(review.id()).as("<seq>.<sub>，seq＝錨點（剛處理完的 PAUSED 事件）").isEqualTo(paused + ".1");
        assertThat(probe.events().stream().map(Frame::id).toList().indexOf(paused))
                .isLessThan(probe.events().stream().map(Frame::id).toList().indexOf(review.id()));
        assertThat(data.get("seq").asInt()).isEqualTo(Integer.parseInt(paused));
        assertThat(data.get("sub").asInt()).isEqualTo(1);
        assertThat(data.get("review").get("kind").asString()).isEqualTo("TASK_CONFIRM");
        assertThat(data.get("review").get("status").asString()).isEqualTo("PENDING");
        assertThat(data.get("review").get("reason").asString()).isEqualTo("Level 1：請確認是否繼續執行任務「設定」");
        assertThat(data.get("review").get("taskName").asString()).isEqualTo("設定");
        assertThat(data.get("review").get("goalName").asString()).isEqualTo("基礎");
        List<String> allowed = new ArrayList<>();
        data.get("review").get("allowedDecisions").forEach(n -> allowed.add(n.asString()));
        assertThat(allowed).containsExactly("APPROVE", "REJECT");
        assertThat(SseProbe.strictlyIncreasing(probe.events())).isTrue();

        // 重連時 Last-Event-ID＝PAUSED 的 id：審核項（子序號 1）嚴格較大，必須重播
        SseProbe again = open(logsPath(run), Map.of("Authorization", "Bearer " + viewer(), "Last-Event-ID", paused));
        assertThat(again.awaitEvent("review-request", Duration.ofSeconds(10))).isNotNull();
        assertThat(again.events().get(0).id()).isEqualTo(paused + ".1");
    }

    @Test
    void anEscalationFailureEndsWithTheStatusChangeThenItsReviewAndTheStreamClosesOnlyAfterThem() {
        Fixture f = prjA("terminal-order", 4);
        MINI.failStepIds.add("G1-T2");
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        SseProbe probe = open(logsPath(run), viewer());
        mini(run).release(5);
        assertThat(probe.awaitEnd(Duration.ofSeconds(20))).isTrue();

        List<Frame> events = probe.events();
        int statusFailed = indexOf(events, "status-change", "runStatus", "FAILED");
        int review = indexOf(events, "review-request", null, null);
        assertThat(statusFailed).isNotNegative();
        assertThat(review).as("終態 status-change 之後才是它衍生的審核項").isGreaterThan(statusFailed);
        assertThat(review).as("審核項是最後一個框架（送完才關閉連線）").isEqualTo(events.size() - 1);
        assertThat(events.get(review).id()).isEqualTo(events.get(statusFailed).id() + ".1");
        assertThat(events.get(review).json().get("review").get("kind").asString()).isEqualTo("ESCALATED");
        Frame alert = probe.events("alert").get(0);
        assertThat(alert.json().get("origin").asString()).isEqualTo("ENGINE");
        assertThat(alert.json().get("code").asString()).isEqualTo("ESCALATION");
        assertThat(alert.json().get("severity").asString()).isEqualTo("CRITICAL");
        assertThat(alert.json().get("rule").asString()).isEqualTo("ENGINE_ESCALATION");
        assertThat(alert.json().get("stepId").asString()).isEqualTo("G1-T2");
        assertThat(alert.json().has("alertId")).isTrue();
        assertThat(SseProbe.strictlyIncreasing(events)).isTrue();
    }

    private static int indexOf(List<Frame> events, String name, String field, String value) {
        for (int i = 0; i < events.size(); i++) {
            Frame frame = events.get(i);
            if (name.equals(frame.event()) && (field == null || value.equals(frame.json().get(field).asString()))) {
                return i;
            }
        }
        return -1;
    }

    @Test
    void aConsoleRuleAlertIsPushedWithAnAnchoredIdAndTheAlertIdAndRule() {
        Fixture f = prjA("console-alert", 4);
        createFixtureTask(f.g2(), "收尾", 4);
        MINI.manualSteps = true;
        MINI.completionDelayMillis = 250;
        String run = startRun(f.projectId(), Map.of("tokenBudget", 2000));
        SseProbe probe = open(logsPath(run), viewer());
        mini(run).release(1);
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t2())))).isTrue();
        mini(run).release(1);
        Frame exceeded = probe.await(fr -> fr.isEvent() && "alert".equals(fr.event())
                && "TOKEN_BUDGET_EXCEEDED".equals(fr.json().path("rule").asString()), Duration.ofSeconds(15));
        assertThat(exceeded).isNotNull();
        assertThat(exceeded.id()).matches("\\d+\\.\\d+");
        assertThat(exceeded.json().get("origin").asString()).isEqualTo("CONSOLE");
        assertThat(exceeded.json().get("severity").asString()).isEqualTo("CRITICAL");
        assertThat(exceeded.json().get("subject").asString()).isEqualTo("run:" + run);
        assertThat(exceeded.json().get("alertId").asString()).isNotBlank();
        assertThat(exceeded.json().get("sub").asInt()).isGreaterThanOrEqualTo(1);
        assertThat(exceeded.json().get("message").asString()).startsWith("Token 使用量已超出預算");
        assertThat(SseProbe.strictlyIncreasing(probe.events())).isTrue();

        // 重連（Last-Event-ID 在它之前）時，Console 自產的告警由資料庫依 event_seq／event_sub 重播
        long[] order = exceeded.order();
        String before = order[0] + "." + (order[1] - 1);
        SseProbe again = open(logsPath(run), Map.of("Authorization", "Bearer " + viewer(), "Last-Event-ID", before));
        Frame replayed = again.await(fr -> fr.isEvent() && exceeded.id().equals(fr.id()), Duration.ofSeconds(10));
        assertThat(replayed).isNotNull();
        assertThat(replayed.json().get("alertId").asString()).isEqualTo(exceeded.json().get("alertId").asString());
    }

    // ── /metrics ────────────────────────────────────────────────────────────────────

    @Test
    void aNewMetricsConnectionFirstGetsThreeSnapshotsWithDistinctIncreasingIdsThenLiveEvents() {
        Fixture f = prjA("metrics-live", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        mini(run).release(1);
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t2())))).isTrue();
        int s = consoleLastSeq(run);

        SseProbe probe = open(metricsPath(run), viewer());
        Frame progress = probe.awaitEvent("progress-update", Duration.ofSeconds(10));
        assertThat(progress).isNotNull();
        assertThat(probe.awaitEvent("metric-update", Duration.ofSeconds(10))).isNotNull();
        List<Frame> snapshot = probe.events().subList(0, 3);
        assertThat(snapshot.stream().map(Frame::event).toList()).containsExactly("progress-update", "token-update",
                "metric-update");
        assertThat(snapshot.stream().map(Frame::id).toList()).containsExactly(s + ".1", s + ".2", s + ".3");
        JsonNode p = snapshot.get(0).json();
        assertThat(p.get("runStatus").asString()).isEqualTo("RUNNING");
        assertThat(p.get("bridgeStatus").asString()).isEqualTo("RUNNING");
        assertThat(p.get("completedSteps").asInt()).isEqualTo(1);
        assertThat(p.get("totalSteps").asInt()).isEqualTo(3);
        assertThat(p.get("progressPct").asDouble()).isEqualTo(33.3);
        assertThat(p.get("currentStep").get("stepId").asString()).isEqualTo("G1-T2");
        assertThat(p.get("currentStep").get("taskName").asString()).isEqualTo("設定");
        JsonNode t = snapshot.get(1).json();
        assertThat(t.get("tokensUsed").asLong()).isEqualTo(1240L);
        assertThat(t.get("contextPct").asDouble()).isEqualTo(0.6);
        assertThat(t.has("tokenBudget")).isTrue();
        JsonNode m = snapshot.get(2).json();
        assertThat(m.get("completedTasks").asInt()).isEqualTo(1);
        assertThat(m.get("totalTasks").asInt()).isEqualTo(3);
        assertThat(m.get("totalTokensUsed").asLong()).isEqualTo(1240L);
        assertThat(m.get("sub").asInt()).isEqualTo(3);

        mini(run).release(5);
        assertThat(probe.awaitEnd(Duration.ofSeconds(20))).isTrue();
        assertThat(SseProbe.strictlyIncreasing(probe.events())).as("快照之後的即時事件 id 嚴格大於 <S>.3").isTrue();
        Frame lastProgress = probe.events("progress-update").get(probe.events("progress-update").size() - 1);
        assertThat(lastProgress.json().get("runStatus").asString()).isEqualTo("COMPLETED");
        assertThat(lastProgress.json().get("progressPct").asDouble()).isEqualTo(100.0);
        Frame lastMetric = probe.events("metric-update").get(probe.events("metric-update").size() - 1);
        assertThat(lastMetric.json().get("completedTasks").asInt()).isEqualTo(3);
        assertThat(lastMetric.json().get("totalTokensUsed").asLong()).isEqualTo(3720L);
        assertThat(probe.events("log")).as("log／alert 不進 /metrics").isEmpty();
        assertThat(probe.events("status-change")).isEmpty();
    }

    @Test
    void connectingToAFinishedRunSendsTheTerminalSnapshotThenClosesAndALastEventIdAtOrBeyondTheLastSnapshotIs204() {
        String run = completedRun("metrics-final");
        int s = consoleLastSeq(run);
        SseProbe probe = open(metricsPath(run), viewer());
        assertThat(probe.awaitEnd(Duration.ofSeconds(10))).isTrue();
        assertThat(probe.events().stream().map(Frame::id).toList()).containsExactly(s + ".1", s + ".2", s + ".3");
        assertThat(probe.events().get(0).json().get("runStatus").asString()).isEqualTo("COMPLETED");
        assertThat(probe.events().get(2).json().get("totalTokensUsed").asLong()).isEqualTo(3720L);
        assertThat(probe.events().get(2).json().get("elapsedSec").asLong()).isNotNegative();

        SseProbe partial = open(metricsPath(run), Map.of("Authorization", "Bearer " + viewer(), "Last-Event-ID", s + ".2"));
        assertThat(partial.awaitEnd(Duration.ofSeconds(10))).isTrue();
        assertThat(partial.events()).as("< <S>.3 → 仍送終態快照後關閉").hasSize(3);
        assertThat(open(metricsPath(run), Map.of("Authorization", "Bearer " + viewer(), "Last-Event-ID", s + ".3"))
                .status()).isEqualTo(204);
        assertThat(open(metricsPath(run), Map.of("Authorization", "Bearer " + viewer(), "Last-Event-ID", String.valueOf(s + 5)))
                .status()).isEqualTo(204);
    }

    @Test
    void metricsStreamForAPausedRunStaysOpenAndKeepsAliveInsteadOfClosing() {
        Fixture f = prjA("metrics-paused", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        api.post(operator(), "/api/v1/executions/" + run + "/pause");
        mini(run).release(1);
        assertThat(awaitProjected(run, "PAUSED")).isTrue();

        SseProbe probe = open(metricsPath(run), viewer());
        Frame progress = probe.awaitEvent("progress-update", Duration.ofSeconds(10));
        assertThat(progress.json().get("runStatus").asString()).isEqualTo("PAUSED");
        assertThat(probe.isEnded()).as("PAUSED 不結束串流").isFalse();
    }

    // ── keep-alive 與連線層告警 ─────────────────────────────────────────────────────

    @Test
    void aQuietStreamGetsKeepAliveCommentsWhichTheParserSeesAsComments() {
        Fixture f = prjA("keepalive", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        SseProbe probe = open(logsPath(run) + "?tail=0", viewer());
        Frame comment = probe.await(Frame::isComment, Duration.ofSeconds(10));
        assertThat(comment).as("測試 profile 的 keep-alive＝2 秒").isNotNull();
        assertThat(comment.comment()).isEqualTo("keep-alive");
        assertThat(comment.id()).isNull();
        assertThat(probe.events()).isEmpty();
    }

    @Test
    void whenTheBridgeIsUnreachableTheStreamStaysOpenAndAnnouncesItOnceWithoutAnIdThenRecovers() {
        Fixture f = prjA("unreachable-stream", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        SseProbe probe = open(logsPath(run) + "?tail=0", viewer());

        setting("autoclaude", "engineUrl", "http://127.0.0.1:1");
        MINI.dropStreams();
        Frame unreachable = probe.await(fr -> fr.isEvent() && "alert".equals(fr.event())
                && "BRIDGE_UNREACHABLE".equals(fr.json().path("code").asString()), Duration.ofSeconds(20));
        assertThat(unreachable).as("Bridge 不可達 → 連線告警，串流不關閉").isNotNull();
        assertThat(unreachable.id()).as("暫態告警不帶 id: 行").isNull();
        assertThat(unreachable.json().get("origin").asString()).isEqualTo("CONSOLE");
        assertThat(unreachable.json().get("severity").asString()).isEqualTo("WARNING");
        sleep(2500);
        assertThat(probe.events("alert").stream().filter(fr -> "BRIDGE_UNREACHABLE".equals(fr.json().path("code").asString()))
                .count()).as("同一次中斷只送一次").isEqualTo(1);
        assertThat(probe.isEnded()).isFalse();

        setting("autoclaude", "engineUrl", MINI.url());
        mini(run).release(5);
        assertThat(probe.awaitEnd(Duration.ofSeconds(30))).as("Bridge 恢復後自動補齊並走到終態").isTrue();
        assertThat(probe.events("status-change").get(probe.events("status-change").size() - 1).json().get("runStatus")
                .asString()).isEqualTo("COMPLETED");
        assertThat(SseProbe.strictlyIncreasing(probe.events())).isTrue();
    }

    @Test
    void whenTheBridgeForgotTheRunTheStreamAnnouncesItAndCloses() {
        Fixture f = prjA("forgotten-stream", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        SseProbe probe = open(logsPath(run) + "?tail=0", viewer());
        MINI.reset();
        Frame unknown = probe.await(fr -> fr.isEvent() && "alert".equals(fr.event())
                && "BRIDGE_RUN_UNKNOWN".equals(fr.json().path("code").asString()), Duration.ofSeconds(20));
        assertThat(unknown).isNotNull();
        assertThat(unknown.id()).isNull();
        assertThat(unknown.json().get("severity").asString()).isEqualTo("WARNING");
        assertThat(probe.awaitEnd(Duration.ofSeconds(10))).isTrue();
        assertThat(runStatus(run)).as("DB 不動").isEqualTo("RUNNING");
    }

    // ── 日誌衛生（TBC-1、AR-05）──────────────────────────────────────────────────────

    @Test
    void aNormallyEndedStreamLeavesNoAccessDeniedErrorsInTheLogAndTheAccessTokenNeverAppearsInAnyLog() {
        String run = completedRun("log-hygiene");
        String secret = viewer();
        for (int i = 0; i < 3; i++) {
            SseProbe viaQuery = open(logsPath(run) + "?access_token=" + secret, (String) null);
            assertThat(viaQuery.awaitEnd(Duration.ofSeconds(10))).isTrue();
        }
        SseProbe metrics = open(metricsPath(run) + "?access_token=" + secret, (String) null);
        assertThat(metrics.awaitEnd(Duration.ofSeconds(10))).isTrue();
        SseProbe bad = open(logsPath(run) + "?access_token=" + secret + "tampered", (String) null);
        assertThat(bad.status()).isEqualTo(401);
        sleep(300);

        List<ILoggingEvent> events;
        synchronized (logs) {
            events = new ArrayList<>(logs.list);
        }
        for (ILoggingEvent event : events) {
            String text = event.getFormattedMessage() + " " + event.getLoggerName() + " " + event.getMDCPropertyMap()
                    + " " + throwableText(event.getThrowableProxy());
            assertThat(text).as("日誌不得含 access_token：" + event.getLoggerName()).doesNotContain(secret)
                    .doesNotContain("access_token=");
            assertThat(text).as("串流正常結束後不得有 AccessDenied（ASYNC dispatch）").doesNotContain("AccessDeniedException")
                    .doesNotContain("AuthorizationDeniedException");
            if (event.getLevel().isGreaterOrEqual(Level.ERROR) && event.getLoggerName().startsWith("com.aisdlc.console")) {
                throw new AssertionError("Console 不應有 ERROR 日誌：" + text);
            }
        }
        assertThat(jdbc.queryForObject("select count(*) from console.audit_log where path like '%access_token%'",
                Long.class)).isZero();
    }

    private static String throwableText(IThrowableProxy proxy) {
        StringBuilder text = new StringBuilder();
        for (IThrowableProxy t = proxy; t != null; t = t.getCause()) {
            text.append(t.getClassName()).append(':').append(t.getMessage()).append(' ');
        }
        return text.toString();
    }
}
