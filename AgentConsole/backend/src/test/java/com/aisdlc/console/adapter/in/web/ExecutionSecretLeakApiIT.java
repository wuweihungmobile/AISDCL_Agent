package com.aisdlc.console.adapter.in.web;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.classic.spi.ThrowableProxyUtil;
import ch.qos.logback.core.read.ListAppender;
import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.SseProbe;
import com.aisdlc.console.support.SseProbe.Frame;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 金鑰與引擎行程編號不外露（契約 §5.0.4 A5：「任何回應與日誌都不含 API 金鑰明文」；§1.2.3、§3.1.2：「不外露 pid」；
 * E2E-14 第 8 列：「回應與日誌沒有 pid」）。為什麼重要：D-11 讓 Console 第一次在每個批次的建立流程裡解密並送出金鑰，D-12 讓回應
 * 第一次帶引擎行程樹的數字——這兩條新路徑上任何一行日誌、任何一個回應欄位多帶了 {@code env}、請求本文或 pid，就等於把它們公開。
 *
 * <p>日誌擷取包含 {@code com.aisdlc.console} 的 TRACE（比正式環境的 INFO 更囉嗦，所以過關的門檻更高）；測試結束還原層級。
 */
class ExecutionSecretLeakApiIT extends AbstractExecutionIT {

    private ListAppender<ILoggingEvent> logs;
    private Logger root;
    private Logger console;
    private Level consoleLevel;
    private final List<SseProbe> probes = new ArrayList<>();

    @BeforeEach
    void captureLogs() {
        root = (Logger) LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME);
        console = (Logger) LoggerFactory.getLogger("com.aisdlc.console");
        consoleLevel = console.getLevel();
        console.setLevel(Level.TRACE);
        logs = new ListAppender<>();
        // 事件消費者、HTTP 執行緒與測試執行緒同時寫日誌：換成並行安全的清單
        logs.list = new CopyOnWriteArrayList<>();
        logs.start();
        root.addAppender(logs);
    }

    @AfterEach
    void releaseLogsAndStreams() {
        root.detachAppender(logs);
        logs.stop();
        console.setLevel(consoleLevel);
        probes.forEach(SseProbe::close);
        probes.clear();
    }

    private SseProbe openLogs(String run) {
        SseProbe probe = SseProbe.open(baseUrl() + "/api/v1/stream/executions/" + run + "/logs",
                Map.of("Authorization", "Bearer " + viewer()));
        probes.add(probe);
        return probe;
    }

    private static String render(ILoggingEvent event) {
        String thrown = event.getThrowableProxy() == null ? "" : "\n" + ThrowableProxyUtil.asString(event.getThrowableProxy());
        return event.getFormattedMessage() + thrown + " " + event.getMDCPropertyMap();
    }

    @Test
    void theApiKeyNeverAppearsInAnyResponseStreamFrameOrLogLineOfARunStartedWithAKey() {
        Fixture f = prjA("secret-leak", 4);
        putApiKey(FAKE_API_KEY);
        MINI.manualSteps = true;

        Resp created = execute(f.projectId(), Map.of("autonomyLevel", 7));
        assertThat(created.status()).isEqualTo(201);
        String run = created.id();
        SseProbe stream = openLogs(run);
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        List<Resp> responses = new ArrayList<>(List.of(created, getRun(run)));
        mini(run).release(10);
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        assertThat(stream.awaitEnd(Duration.ofSeconds(10))).isTrue();

        String execution = "/api/v1/executions/" + run;
        String monitor = "/api/v1/monitor/projects/" + f.projectId();
        for (String path : List.of(execution, execution + "/steps", execution + "/dag", execution + "/checkpoints",
                "/api/v1/projects/" + f.projectId() + "/executions", "/api/v1/notifications/summary",
                monitor + "/metrics", monitor + "/logs", monitor + "/alerts", "/api/v1/settings",
                "/api/v1/settings/model")) {
            Resp resp = api.get(viewer(), path);
            assertThat(resp.status()).as(path).isEqualTo(200);
            responses.add(resp);
        }

        assertThat(responses).hasSize(13).allSatisfy(resp -> assertThat(resp.body()).doesNotContain(FAKE_API_KEY));
        assertThat(stream.events()).as("SSE 串流有收到框架（排除「本來就沒有」的假通過）").isNotEmpty()
                .allSatisfy(frame -> assertThat(frame.data()).doesNotContain(FAKE_API_KEY));
        assertThat(logs.list).as("有擷取到日誌（排除「本來就沒有」的假通過）").isNotEmpty();
        assertThat(logs.list.stream().map(ExecutionSecretLeakApiIT::render).toList())
                .noneMatch(line -> line.contains(FAKE_API_KEY));
    }

    @Test
    void theEnginePidNeverAppearsInTheDetailOrInTheLiveStatusStreamAndTheStartedStatusKeepsItsOtherWords() {
        Fixture f = prjA("pid-leak", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        SseProbe stream = openLogs(run);
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();

        Resp detail = getRun(run);
        // 迷你 Bridge 與真 Bridge 同形：狀態文字「引擎已啟動（pid=…，第 1 次 spawn）」、快照有 pid 欄位
        assertThat(mini(run).reason()).contains("pid=");
        assertThat(detail.<String>read("$.data.reason")).isEqualTo("引擎已啟動（第 1 次 spawn）");
        assertThat(detail.body()).as("詳情整份都沒有 pid（只比單字，stepId 裡的 pId 不算）").doesNotContainPattern("(?i)\\bpid\\b");

        Frame started = stream.await(f2 -> "status-change".equals(f2.event())
                && "RUNNING".equals(f2.json().get("runStatus").asString())
                && f2.json().get("reason").asString().startsWith("引擎已啟動"), Duration.ofSeconds(10));
        assertThat(started).as("即時串流收到「已啟動」的狀態框架").isNotNull();
        assertThat(started.json().get("reason").asString()).isEqualTo("引擎已啟動（第 1 次 spawn）");

        // 告警文字同樣清過（強制終止的告警會帶行程編號清單）
        mini(run).inject("alert", Map.of("level", "warning", "code", "FORCE_KILL",
                "message", "終止訊號後 5s 仍未退出，已強制終止 pid=[4242, 4243]"));
        Frame alert = stream.awaitEvent("alert", Duration.ofSeconds(10));
        assertThat(alert).isNotNull();
        assertThat(alert.json().get("message").asString()).isEqualTo("終止訊號後 5s 仍未退出，已強制終止");

        mini(run).release(10);
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        assertThat(stream.awaitEnd(Duration.ofSeconds(10))).isTrue();
        for (Frame frame : stream.events()) {
            assertThat(frame.data()).as(frame.event() + " 框架").doesNotContainPattern("(?i)\\bpid\\b");
        }
        assertThat(logs.list.stream().map(ExecutionSecretLeakApiIT::render).toList()).as("日誌也沒有 pid")
                .noneMatch(line -> line.matches("(?is).*\\bpid\\b.*"));
    }
}
