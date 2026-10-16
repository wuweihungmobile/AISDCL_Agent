package com.aisdlc.console.adapter.in.web;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.classic.spi.IThrowableProxy;
import ch.qos.logback.core.read.ListAppender;
import com.aisdlc.console.application.service.RunEventHub;
import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.SseProbe;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SSE 客戶端中途斷線（DEF-AC-014；契約 §2；{@code API-SSE-01}、{@code API-SSE-02}）——對真的 HTTP 伺服器開串流、讀到第一個框架後<b>關掉連線</b>，
 * 等伺服器的下一次寫出（測試 profile 的 keep-alive 是 2 秒）撞上已死的連線、Tomcat 通知 Spring、Spring 以非同步分派收尾，然後斷言：
 * ①日誌沒有任何 WARN／ERROR（修好之前會有一筆 ERROR「未預期的例外」，緊接著一筆寫不出 {@code ApiError} 的 WARN
 * 「Failure in @ExceptionHandler」）；②例外處理器以一行 DEBUG 記下「客戶端已斷線」，帶 runId 與<b>該請求自己的</b> traceId；
 * ③串流的訂閱已釋放（{@code RunEventHub} 不再有這個 run 的訂閱者）。
 * 為什麼重要：關頁面、{@code EventSource.close()}、網路中斷都是 SSE 的日常，不是故障；每次都記 ERROR 會污染以日誌級別計數或告警的監控，
 * 真正的錯誤反而看不出來。
 */
class StreamDisconnectApiIT extends AbstractExecutionIT {

    private static final Duration PATIENCE = Duration.ofSeconds(20);

    @Autowired
    RunEventHub hub;

    private ListAppender<ILoggingEvent> logs;
    private Logger root;
    private Logger handlerLogger;
    private Level handlerLevelBefore;
    private final List<SseProbe> probes = new ArrayList<>();

    @BeforeEach
    void captureLogs() {
        root = (Logger) LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME);
        logs = new ListAppender<>();
        logs.start();
        root.addAppender(logs);
        // 「斷線被當成正常結束」的那一行是 DEBUG：開到 DEBUG 它才留得下來，也是本測試等待「例外處理器已跑完」的訊號
        handlerLogger = (Logger) LoggerFactory.getLogger(GlobalExceptionHandler.class);
        handlerLevelBefore = handlerLogger.getLevel();
        handlerLogger.setLevel(Level.DEBUG);
    }

    @AfterEach
    void releaseLogsAndStreams() {
        handlerLogger.setLevel(handlerLevelBefore);
        root.detachAppender(logs);
        logs.stop();
        probes.forEach(SseProbe::close);
        probes.clear();
    }

    private List<ILoggingEvent> snapshot() {
        synchronized (logs) {
            return new ArrayList<>(logs.list);
        }
    }

    /** {@code mark} 之後 WARN 以上的事件，一筆一行（等級、logger、訊息、例外鏈），失敗訊息可直接看出是哪一筆。 */
    private List<String> problemsAfter(int mark) {
        List<ILoggingEvent> events = snapshot();
        return events.subList(Math.min(mark, events.size()), events.size()).stream()
                .filter(event -> event.getLevel().isGreaterOrEqual(Level.WARN))
                .map(event -> event.getLevel() + " " + event.getLoggerName() + " | " + event.getFormattedMessage()
                        + " | " + throwableText(event.getThrowableProxy()))
                .toList();
    }

    /** 例外處理器對這個 run 記的「客戶端已斷線」DEBUG 行（沒有回 null）。 */
    private ILoggingEvent quietLine(int mark, String run) {
        List<ILoggingEvent> events = snapshot();
        return events.subList(Math.min(mark, events.size()), events.size()).stream()
                .filter(event -> event.getLevel() == Level.DEBUG
                        && event.getLoggerName().equals(GlobalExceptionHandler.class.getName())
                        && event.getFormattedMessage().contains(run))
                .findFirst().orElse(null);
    }

    private static String throwableText(IThrowableProxy proxy) {
        StringBuilder text = new StringBuilder();
        for (IThrowableProxy t = proxy; t != null; t = t.getCause()) {
            text.append(t.getClassName()).append(':').append(t.getMessage()).append(' ');
        }
        return text.toString().strip();
    }

    /** 開一個還在跑的 run 與一條串流，等到第一個框架。 */
    private SseProbe openLiveStream(String run, String path) {
        SseProbe probe = SseProbe.open(baseUrl() + "/api/v1/stream/executions/" + run + path,
                Map.of("Authorization", "Bearer " + viewer()));
        probes.add(probe);
        assertThat(probe.await(frame -> true, Duration.ofSeconds(10))).as("收到第一個框架").isNotNull();
        return probe;
    }

    private String startLiveRun(String name) {
        Fixture fixture = prjA(name, 4);
        MINI.manualSteps = true;
        String run = startRun(fixture.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(fixture.t1())))).isTrue();
        return run;
    }

    /** 斷線之後等到「已記下安靜的一行」或「出現 WARN／ERROR」其中一個（修好前是後者），再逐項斷言。 */
    private void assertTheDisconnectEndedQuietly(int mark, String run, String traceId) {
        awaitUntil(PATIENCE, () -> quietLine(mark, run) != null || !problemsAfter(mark).isEmpty());

        assertThat(problemsAfter(mark)).as("客戶端斷線不是錯誤：日誌不得有 WARN／ERROR").isEmpty();
        ILoggingEvent line = quietLine(mark, run);
        assertThat(line).as("例外處理器把斷線當成正常結束，記了一行 DEBUG").isNotNull();
        assertThat(line.getFormattedMessage()).contains("run=" + run).contains("traceId=" + traceId);
        assertThat(awaitUntil(PATIENCE, () -> hub.subscriberCount(UUID.fromString(run)) == 0))
                .as("串流的訂閱已釋放").isTrue();
    }

    @Test
    void aLogsClientThatLeavesMidStreamEndsQuietlyAndFreesItsSubscription() {
        String run = startLiveRun("gone-logs");
        SseProbe probe = openLiveStream(run, "/logs");
        assertThat(hub.subscriberCount(UUID.fromString(run))).isEqualTo(1);
        String traceId = probe.header("X-Trace-Id");
        assertThat(traceId).as("串流回應帶這個請求自己的 X-Trace-Id").isNotBlank();
        int mark = snapshot().size();

        probe.close();

        assertTheDisconnectEndedQuietly(mark, run, traceId);
    }

    @Test
    void aMetricsClientThatLeavesMidStreamEndsQuietlyAndFreesItsSubscription() {
        String run = startLiveRun("gone-metrics");
        SseProbe probe = openLiveStream(run, "/metrics");
        assertThat(hub.subscriberCount(UUID.fromString(run))).isEqualTo(1);
        String traceId = probe.header("X-Trace-Id");
        assertThat(traceId).isNotBlank();
        int mark = snapshot().size();

        probe.close();

        assertTheDisconnectEndedQuietly(mark, run, traceId);
    }

    @Test
    void aClientThatLeavesWhileEventsAreStillFlowingEndsQuietlyToo() {
        String run = startLiveRun("gone-busy");
        SseProbe probe = openLiveStream(run, "/logs?tail=0");
        String traceId = probe.header("X-Trace-Id");
        int mark = snapshot().size();

        probe.close();
        mini(run).release(5);

        assertThat(awaitProjected(run, "COMPLETED")).as("run 照常走完，斷線的串流不影響執行").isTrue();
        assertTheDisconnectEndedQuietly(mark, run, traceId);
    }
}
