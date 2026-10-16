package com.aisdlc.console.adapter.out.bridge;

import com.aisdlc.console.application.port.out.AgentBridge.BridgeEvent;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AgentBridge.RunSnapshot;
import com.aisdlc.console.application.port.out.AgentBridge.RunStarted;
import com.aisdlc.console.application.port.out.AgentBridge.StartRunRequest;
import com.aisdlc.console.application.port.out.SettingValues;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.ResourceUsage;
import com.aisdlc.console.infrastructure.config.BridgeProperties;
import com.aisdlc.minibridge.MiniBridge;
import com.aisdlc.minibridge.MiniRun;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.web.client.RestClient;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * runs 系列的 Bridge 出站介面卡（契約 §3.1），對<b>真的 HTTP／SSE</b>（迷你 Bridge）驗：請求欄位、狀態分流、事件正規化、
 * SSE 閒置看門狗。為什麼重要：Bridge 的 {@code extra=forbid} 會因為多一個欄位整個拒絕；SSE 閒置逾時是「Bridge 沒死但不說話」
 * 時唯一的斷線偵測，沒有它消費者會永遠卡住。
 */
class BridgeRunsAdapterTest {

    private static MiniBridge mini;
    private BridgeHttpAdapter adapter;

    @BeforeAll
    static void startMini() {
        mini = MiniBridge.start(null);
    }

    @AfterAll
    static void stopMini() {
        mini.close();
    }

    @BeforeEach
    void setUp() {
        mini.reset();
        adapter = adapterFor(mini.url());
    }

    private static BridgeHttpAdapter adapterFor(String url) {
        SettingValues settings = new SettingValues() {
            @Override
            public Optional<String> find(String category, String key) {
                return Optional.empty();
            }

            @Override
            public Optional<String> findCustomized(String category, String key) {
                return Optional.empty();
            }
        };
        return new BridgeHttpAdapter(RestClient.builder(), new BridgeEndpoints(settings, new BridgeProperties(url)),
                new JdkRequestFactoryProvider());
    }

    private static Map<String, Object> playbook(String... stepNames) {
        List<Map<String, Object>> tasks = new ArrayList<>();
        for (int i = 0; i < stepNames.length; i++) {
            Map<String, Object> task = new HashMap<>();
            task.put("step_id", "G1-T" + (i + 1));
            task.put("name", stepNames[i]);
            task.put("prompt", "## 任務 G1-T" + (i + 1) + "：" + stepNames[i]);
            task.put("max_retries", 1);
            task.put("goal_task_id", UUID.randomUUID().toString());
            tasks.add(task);
        }
        Map<String, Object> playbook = new HashMap<>();
        playbook.put("version", "1.0");
        playbook.put("project", "demo");
        playbook.put("tasks", tasks);
        return playbook;
    }

    private RunStarted start(UUID runId, String path, String... steps) {
        return adapter.startRun(new StartRunRequest(runId, "demo", path, playbook(steps),
                Map.of("claude", Map.of("command", "aisdlc-mock-claude")), Map.of("MOCK_CLAUDE_DELAY", "0.1"), false));
    }

    @Test
    void startRunPostsTheDocumentedBodyAndReturnsTheRunningRun() {
        UUID id = UUID.randomUUID();

        RunStarted started = start(id, "/work/a", "一", "二");

        assertThat(started.runId()).isEqualTo(id.toString());
        assertThat(started.status()).isEqualTo(BridgeStatus.RUNNING);
        assertThat(started.bridgeInstance()).isEqualTo("mini-bridge");
        Map<String, Object> request = mini.run(id).request;
        assertThat(request.keySet()).containsExactlyInAnyOrder("run_id", "project", "execution_path", "playbook",
                "config_overrides", "env", "fresh");
        assertThat(request).containsEntry("execution_path", "/work/a").containsEntry("fresh", false);
        assertThat(request.get("env")).isEqualTo(Map.of("MOCK_CLAUDE_DELAY", "0.1"));
    }

    @Test
    void aRunProgressesToCompletedAndTheSnapshotAndNormalizedEventsAgree() {
        UUID id = UUID.randomUUID();
        start(id, "/work/b", "一", "二");
        assertThat(mini.run(id).awaitStatus("COMPLETED", Duration.ofSeconds(10))).isTrue();

        RunSnapshot snapshot = adapter.getRun(id);
        assertThat(snapshot.status()).isEqualTo(BridgeStatus.COMPLETED);
        assertThat(snapshot.completedSteps()).isEqualTo(2);
        assertThat(snapshot.totalSteps()).isEqualTo(2);
        assertThat(snapshot.tokensUsed()).isEqualTo(2480L);
        assertThat(snapshot.lastEventSeq()).isEqualTo(mini.run(id).lastSeq());

        List<BridgeEvent> events = adapter.listEvents(id, 0, 500);
        assertThat(events).extracting(BridgeEvent::seq).isSorted().doesNotHaveDuplicates();
        assertThat(events).extracting(BridgeEvent::event).startsWith("status", "status", "step");
        BridgeEvent step = events.stream().filter(e -> e.event().equals("step")).findFirst().orElseThrow();
        assertThat(step.data()).doesNotContainKey("event").containsEntry("step_id", "G1-T1");
        assertThat(step.text("status")).isEqualTo("STARTED");
        assertThat(step.integer("step_number")).isEqualTo(1);
        assertThat(adapter.listEvents(id, events.get(2).seq(), 500)).hasSize(events.size() - 3);
        assertThat(adapter.listEvents(id, 0, 3)).hasSize(3);
    }

    @Test
    void pauseStopsAtTheNextStepBoundaryAndResumeContinuesFromThere() throws InterruptedException {
        UUID id = UUID.randomUUID();
        mini.manualSteps = true;
        start(id, "/work/c", "一", "二", "三");
        MiniRun run = mini.run(id);
        awaitEvents(run, "STARTED", 1);

        assertThat(adapter.pauseRun(id)).isEqualTo(BridgeStatus.PAUSING);
        assertThat(adapter.pauseRun(id)).as("PAUSING 時冪等").isEqualTo(BridgeStatus.PAUSING);
        run.release(1);
        assertThat(run.awaitStatus("PAUSED", Duration.ofSeconds(10))).isTrue();
        assertThat(adapter.getRun(id).completedSteps()).isEqualTo(1);
        assertThat(run.reason()).contains("在步驟邊界暫停").contains("已完成 1 步");

        assertThat(adapter.resumeRun(id, Map.of())).isEqualTo(BridgeStatus.RUNNING);
        run.release(10);
        assertThat(run.awaitStatus("COMPLETED", Duration.ofSeconds(10))).isTrue();
        assertThat(run.checkpointNames()).containsExactly("after-G1-T1", "after-G1-T2", "after-G1-T3");
        assertThat(run.checkpointStepIndexes()).containsExactly(1, 2, 3);
    }

    private static void awaitEvents(MiniRun run, String stepStatus, int count) throws InterruptedException {
        for (int i = 0; i < 200; i++) {
            long seen = run.events().stream().filter(e -> "step".equals(e.get("event"))
                    && stepStatus.equals(e.get("status"))).count();
            if (seen >= count) {
                return;
            }
            Thread.sleep(25);
        }
        throw new AssertionError("等不到 " + count + " 則 " + stepStatus);
    }

    @Test
    void stopCancelsAndRestoreRewindsACompletedRunToAnEarlierCheckpoint() {
        UUID id = UUID.randomUUID();
        start(id, "/work/d", "一", "二");
        assertThat(mini.run(id).awaitStatus("COMPLETED", Duration.ofSeconds(10))).isTrue();
        UUID first = mini.run(id).checkpointIds().get(0);

        adapter.restoreRun(id, first, Map.of());

        assertThat(mini.run(id).awaitStatus("COMPLETED", Duration.ofSeconds(10))).isTrue();
        assertThat(adapter.getRun(id).tokensUsed()).as("累計跨 restore 持續（2 步＋重跑第 2 步）").isEqualTo(3720L);
        assertThat(mini.run(id).events().stream().filter(e -> "alert".equals(e.get("event")))).singleElement()
                .satisfies(e -> assertThat(e.get("code")).isEqualTo("RESTORE"));
    }

    @Test
    void bridgeRejectionsKeepTheirStatusAndReason() {
        UUID id = UUID.randomUUID();
        start(id, "/work/e", "一");
        assertThat(mini.run(id).awaitStatus("COMPLETED", Duration.ofSeconds(10))).isTrue();

        assertThatThrownBy(() -> adapter.pauseRun(id)).isInstanceOfSatisfying(BridgeRejectedException.class, e -> {
            assertThat(e.status()).isEqualTo(409);
            assertThat(e.reason()).isEqualTo("invalid_state");
            assertThat(e.body()).containsEntry("status", "COMPLETED");
        });
        assertThatThrownBy(() -> adapter.getRun(UUID.randomUUID())).isInstanceOfSatisfying(
                BridgeRejectedException.class, e -> {
                    assertThat(e.status()).isEqualTo(404);
                    assertThat(e.reason()).isEqualTo("run_not_found");
                });
        assertThat(start(UUID.randomUUID(), "/work/e", "一").status()).as("同 project＋path 的鎖已釋放，不衝突")
                .isEqualTo(BridgeStatus.RUNNING);
    }

    @Test
    void aSecondRunOnTheSameProjectAndPathWhileTheFirstIsActiveIsA409WithTheHolder() {
        UUID first = UUID.randomUUID();
        mini.manualSteps = true;
        start(first, "/work/f", "一");

        assertThatThrownBy(() -> start(UUID.randomUUID(), "/work/f", "一")).isInstanceOfSatisfying(
                BridgeRejectedException.class, e -> {
                    assertThat(e.status()).isEqualTo(409);
                    assertThat(e.reason()).isEqualTo("advisory_lock_held");
                    assertThat(e.body()).containsEntry("holder_run_id", first.toString());
                });
        mini.run(first).release(10);
    }

    @Test
    void streamEventsDeliversEveryEventInOrderAndReturnsWhenTheRunEnds() {
        UUID id = UUID.randomUUID();
        start(id, "/work/g", "一", "二");
        List<BridgeEvent> received = new CopyOnWriteArrayList<>();

        adapter.streamEvents(id, 0, Duration.ofSeconds(10), received::add);

        assertThat(received).extracting(BridgeEvent::seq).isSorted().doesNotHaveDuplicates().first().isEqualTo(1);
        assertThat(received.get(received.size() - 1).event()).isEqualTo("status");
        assertThat(received.get(received.size() - 1).text("status")).isEqualTo("COMPLETED");
        assertThat(received).hasSize(mini.run(id).events().size());

        List<BridgeEvent> tail = new ArrayList<>();
        adapter.streamEvents(id, received.get(received.size() - 3).seq(), Duration.ofSeconds(10), tail::add);
        assertThat(tail).hasSize(2).extracting(BridgeEvent::seq).containsExactly(received.get(received.size() - 2).seq(),
                received.get(received.size() - 1).seq());
    }

    @Test
    void anIdleStreamIsCutAfterTheIdleTimeoutButKeepAliveCommentsKeepItAlive() throws InterruptedException {
        UUID id = UUID.randomUUID();
        mini.manualSteps = true;
        mini.keepAliveMillis = 60_000;
        start(id, "/work/h", "一");
        long begin = System.nanoTime();

        assertThatThrownBy(() -> adapter.streamEvents(id, 0, Duration.ofMillis(400), e -> { }))
                .isInstanceOf(UpstreamException.TimedOut.class);
        assertThat(Duration.ofNanos(System.nanoTime() - begin)).isBetween(Duration.ofMillis(300), Duration.ofSeconds(5));

        mini.keepAliveMillis = 100;
        Thread releaser = Thread.ofVirtual().start(() -> {
            try {
                Thread.sleep(1200);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            mini.run(id).release(10);
        });
        List<BridgeEvent> received = new ArrayList<>();
        adapter.streamEvents(id, 0, Duration.ofMillis(400), received::add);
        releaser.join();
        assertThat(received.get(received.size() - 1).text("status")).isEqualTo("COMPLETED");
    }

    @Test
    void anUnknownRunOnTheStreamIsA404RejectionAndAnUnreachableBridgeIsUnavailable() {
        assertThatThrownBy(() -> adapter.streamEvents(UUID.randomUUID(), 0, Duration.ofSeconds(2), e -> { }))
                .isInstanceOfSatisfying(BridgeRejectedException.class, e -> assertThat(e.status()).isEqualTo(404));

        BridgeHttpAdapter dead = adapterFor("http://127.0.0.1:1");
        assertThatThrownBy(() -> dead.getRun(UUID.randomUUID())).isInstanceOf(UpstreamException.Unavailable.class);
        assertThatThrownBy(() -> dead.streamEvents(UUID.randomUUID(), 0, Duration.ofSeconds(2), e -> { }))
                .isInstanceOf(UpstreamException.Unavailable.class);
        assertThatThrownBy(() -> dead.pauseRun(UUID.randomUUID())).isInstanceOf(UpstreamException.Unavailable.class);
    }

    @Test
    void droppedStreamsSurfaceAsAnErrorSoTheConsumerCanReconnect() {
        UUID id = UUID.randomUUID();
        mini.manualSteps = true;
        start(id, "/work/i", "一");
        Thread dropper = Thread.ofVirtual().start(() -> {
            try {
                Thread.sleep(300);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            mini.dropStreams();
        });

        assertThatThrownBy(() -> adapter.streamEvents(id, 0, Duration.ofSeconds(5), e -> { }))
                .isInstanceOf(UpstreamException.class);
        mini.run(id).release(10);
        dropperJoin(dropper);
    }

    private static void dropperJoin(Thread thread) {
        try {
            thread.join();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    // ── D-12：RunStateOut.resources（契約 §3.1.2）──────────────────────────────────────────────
    // 為什麼重要：資源取樣只是顯示用的輔助資料。Bridge 的回應少一個鍵、值為 null、或欄位不齊，都不可以讓整個批次詳情失敗——
    // 這裡解析錯誤（丟例外）會讓「執行頁」在舊版 Bridge 上整頁 5xx；而解析太鬆（猜缺的欄位）會顯示不存在的數字。

    @Test
    void theSnapshotCarriesTheResourceSampleWhileTheEngineIsAlive()
            throws InterruptedException {
        UUID id = UUID.randomUUID();
        mini.manualSteps = true;
        start(id, "/work/res-a", "一", "二");
        MiniRun run = mini.run(id);
        awaitEvents(run, "STARTED", 1);

        ResourceUsage alive = adapter.getRun(id).resources();
        assertThat(alive).as("引擎行程樹存活：原樣帶出迷你 Bridge 的樣本（欄位對映與型別）")
                .isEqualTo(new ResourceUsage(12.3, 361_758_720L, 3, "2026-10-16T03:21:45.123456+00:00"));

        run.release(10);
        assertThat(run.awaitStatus("COMPLETED", Duration.ofSeconds(10))).isTrue();
        assertThat(adapter.getRun(id).resources()).as("終態沒有行程").isNull();
    }

    @Test
    void aNullOrMissingResourcesKeyIsNullAndTheRestIsIntact() {
        UUID id = UUID.randomUUID();
        mini.manualSteps = true;
        start(id, "/work/res-b", "一");

        mini.resourcesMode = MiniBridge.ResourcesMode.NULL;
        RunSnapshot withNull = adapter.getRun(id);
        mini.resourcesMode = MiniBridge.ResourcesMode.OMIT;
        RunSnapshot withoutKey = adapter.getRun(id);

        assertThat(withNull.resources()).isNull();
        assertThat(withoutKey.resources()).as("舊版 Bridge 的回應沒有這個鍵").isNull();
        assertThat(withNull.status()).isEqualTo(withoutKey.status()).isEqualTo(BridgeStatus.RUNNING);
        assertThat(withNull.runId()).isEqualTo(id.toString());
        mini.run(id).release(10);
    }

    @Test
    void resourcesNeedAllFourFieldsWithTheRightTypes() {
        Map<String, Object> full = Map.of("cpu_percent", 0, "rss_bytes", 1L, "process_count", 1,
                "sampled_at", "2026-10-16T03:21:45+00:00");
        assertThat(BridgeHttpAdapter.resourcesOf(full)).as("整數的 cpu_percent（例：0）也是數字")
                .isEqualTo(new ResourceUsage(0.0, 1L, 1, "2026-10-16T03:21:45+00:00"));

        assertThat(BridgeHttpAdapter.resourcesOf(null)).isNull();
        assertThat(BridgeHttpAdapter.resourcesOf("not an object")).isNull();
        assertThat(BridgeHttpAdapter.resourcesOf(List.of(full))).isNull();
        assertThat(BridgeHttpAdapter.resourcesOf(Map.of())).isNull();
        for (String missing : full.keySet()) {
            Map<String, Object> partial = new HashMap<>(full);
            partial.remove(missing);
            assertThat(BridgeHttpAdapter.resourcesOf(partial)).as("缺 " + missing).isNull();
        }
        for (Map.Entry<String, Object> wrong : Map.<String, Object>of("cpu_percent", "12.3", "rss_bytes", "1",
                "process_count", "1", "sampled_at", 20261016).entrySet()) {
            Map<String, Object> bad = new HashMap<>(full);
            bad.put(wrong.getKey(), wrong.getValue());
            assertThat(BridgeHttpAdapter.resourcesOf(bad)).as(wrong.getKey() + " 型別不符").isNull();
        }
        Map<String, Object> blankTime = new HashMap<>(full);
        blankTime.put("sampled_at", "  ");
        assertThat(BridgeHttpAdapter.resourcesOf(blankTime)).as("沒有取樣時間＝無法判斷新鮮度，不採用").isNull();
    }

    // ── 狀態文字不外露 pid（契約 §1.2.3；BridgeText）────────────────────────────────────────────

    @Test
    void theStatusTextOfASnapshotAndOfItsEventsNeverCarriesTheEnginePid() throws InterruptedException {
        UUID id = UUID.randomUUID();
        mini.manualSteps = true;
        start(id, "/work/res-c", "一");
        MiniRun run = mini.run(id);
        awaitEvents(run, "STARTED", 1);
        assertThat(run.reason()).as("迷你 Bridge 與真 Bridge 同形：狀態文字帶 pid").contains("pid=");

        String reason = adapter.getRun(id).reason();
        assertThat(reason).isEqualTo("引擎已啟動（第 1 次 spawn）");

        List<BridgeEvent> events = adapter.listEvents(id, 0, 500);
        assertThat(events.stream().filter(e -> e.event().equals("status")).map(e -> e.text("reason")))
                .contains("引擎已啟動（第 1 次 spawn）").noneMatch(text -> text != null && text.contains("pid"));
        List<BridgeEvent> streamed = new CopyOnWriteArrayList<>();
        run.release(10);
        adapter.streamEvents(id, 0, Duration.ofSeconds(10), streamed::add);
        assertThat(streamed.stream().filter(e -> e.event().equals("status")).map(e -> e.text("reason")))
                .as("SSE 串流的事件同樣清過").isNotEmpty().noneMatch(text -> text != null && text.contains("pid"));
    }

    @Test
    void anAlertMessageThatMentionsPidsIsCleanedToo() {
        UUID id = UUID.randomUUID();
        start(id, "/work/res-d", "一");
        assertThat(mini.run(id).awaitStatus("COMPLETED", Duration.ofSeconds(10))).isTrue();
        mini.run(id).inject("alert", Map.of("level", "warning", "code", "FORCE_KILL",
                "message", "終止訊號後 5s 仍未退出，已強制終止 pid=[4242, 4243]"));

        List<BridgeEvent> events = adapter.listEvents(id, 0, 500);

        BridgeEvent alert = events.stream().filter(e -> e.event().equals("alert")).findFirst().orElseThrow();
        assertThat(alert.text("message")).isEqualTo("終止訊號後 5s 仍未退出，已強制終止");
        assertThat(alert.text("code")).as("其他欄位不動").isEqualTo("FORCE_KILL");
    }

    // ── X-Trace-Id（契約 §0.4 第 6 點、§3.1.1，C-12；NFR-9.4-04）────────────────────────────────
    // 為什麼重要：同一次使用者操作的 console-api 日誌、Bridge 日誌與前端錯誤封包的 traceId 要能用同一個值串起來——
    // 任何一種呼叫漏帶標頭（尤其是 SSE 串流與健康探測，它們走的是不同的 HTTP 客戶端），那一段日誌就斷線了。

    private static final Pattern UUID_FORMAT = Pattern.compile(
            "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}");

    private List<String> tracedRequests() {
        return mini.traced().stream().map(MiniBridge.Traced::request).toList();
    }

    /** 對迷你 Bridge 做「契約 §3.1 呼叫總表」裡每一種 runs／health 請求各一次（含 SSE 串流）。 */
    private void callEveryRunsEndpointOnce(UUID id) {
        adapter.health();
        start(id, "/work/trace", "一", "二");
        assertThat(mini.run(id).awaitStatus("COMPLETED", Duration.ofSeconds(10))).isTrue();
        adapter.getRun(id);
        adapter.listEvents(id, 0, 500);
        adapter.streamEvents(id, 0, Duration.ofSeconds(10), e -> { });
        UUID first = mini.run(id).checkpointIds().get(0);
        adapter.restoreRun(id, first, Map.of());
        assertThat(mini.run(id).awaitStatus("COMPLETED", Duration.ofSeconds(10))).isTrue();
        assertThatThrownBy(() -> adapter.pauseRun(id)).isInstanceOf(BridgeRejectedException.class);
        assertThatThrownBy(() -> adapter.resumeRun(id, Map.of())).isInstanceOf(BridgeRejectedException.class);
        assertThatThrownBy(() -> adapter.stopRun(id)).isInstanceOf(BridgeRejectedException.class);
    }

    @Test
    void everyRequestOfEveryKindCarriesTheTraceIdOfTheCallingThread() {
        UUID id = UUID.randomUUID();
        MDC.put("traceId", "0f7c2a58-4e1d-4b29-9d3e-6a1b5c8d9e02");
        try {
            callEveryRunsEndpointOnce(id);
        } finally {
            MDC.remove("traceId");
        }

        assertThat(tracedRequests()).contains("GET /health/deep", "POST /autoclaude/runs", "GET /autoclaude/runs/" + id,
                "GET /autoclaude/runs/" + id + "/events",
                "GET /autoclaude/runs/" + id + "/stream", "POST /autoclaude/runs/" + id + "/restore",
                "POST /autoclaude/runs/" + id + ":pause", "POST /autoclaude/runs/" + id + ":resume",
                "POST /autoclaude/runs/" + id + ":stop");
        assertThat(mini.traced()).as("沒有任何一個請求漏帶，也沒有被換成別的值")
                .extracting(MiniBridge.Traced::traceId).containsOnly("0f7c2a58-4e1d-4b29-9d3e-6a1b5c8d9e02");
    }

    @Test
    void aThreadWithoutAnyTraceContextStillSendsOneGeneratedPerCallNeverNothing() {
        UUID id = UUID.randomUUID();

        callEveryRunsEndpointOnce(id);

        assertThat(mini.traced()).as("探測環等背景工作：每個請求都有一個新產的 UUID").isNotEmpty()
                .allSatisfy(t -> assertThat(t.traceId()).matches(UUID_FORMAT));
        assertThat(mini.traced().stream().filter(t -> t.request().equals("GET /health/deep"))
                .map(MiniBridge.Traced::traceId)).isNotEmpty();
        assertThat(mini.traced().stream().map(MiniBridge.Traced::traceId).distinct().count())
                .as("沒有上下文時每次呼叫各自新產（不是共用一個全域值）").isGreaterThan(1);
    }
}
