package com.aisdlc.console.adapter.out.bridge;

import com.aisdlc.console.application.port.out.AgentBridge.BridgeCheckpoint;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeEvent;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AgentBridge.RunSnapshot;
import com.aisdlc.console.application.port.out.AgentBridge.RunStarted;
import com.aisdlc.console.application.port.out.AgentBridge.StartRunRequest;
import com.aisdlc.console.application.port.out.SettingValues;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.infrastructure.config.BridgeProperties;
import com.aisdlc.minibridge.MiniBridge;
import com.aisdlc.minibridge.MiniRun;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;

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
        assertThat(adapter.listCheckpoints(id)).extracting(BridgeCheckpoint::name)
                .containsExactly("after-G1-T1", "after-G1-T2", "after-G1-T3");
        assertThat(adapter.listCheckpoints(id)).extracting(BridgeCheckpoint::stepIdx).containsExactly(1, 2, 3);
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
        UUID first = UUID.fromString(adapter.listCheckpoints(id).get(0).checkpointId());

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
}
