package com.aisdlc.console.application.service;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Frame;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Kind;
import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeEvent;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.port.out.ResearchBridge;
import com.aisdlc.console.application.port.out.ResearchProjectReadPort;
import com.aisdlc.console.application.port.out.RuntimeSettings;
import com.aisdlc.console.application.service.RunEventProcessor.Outcome;
import com.aisdlc.console.domain.exception.ResearchBridgeException;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.RunStatus;
import org.junit.jupiter.api.Test;
import org.mockito.stubbing.Answer;
import org.slf4j.LoggerFactory;
import org.springframework.transaction.PlatformTransactionManager;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.function.Consumer;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 自癒同步通知（AT-962-9-6、9-E-1、9-E-2；AC-R2P-16-1）。為什麼重要：看板與自癒監視器靠「事件交易提交後」才通知研究面同步日誌——
 * 通知排在提交之前會讓 Bridge 讀到舊視圖；排在 SSE 發佈之後會被發佈失敗拖累；非研究專案也打 Bridge 是無謂外呼；Bridge 掛掉若讓例外外洩，事件投影與前端串流都會中斷。
 */
class ResearchHealingNotifierTest {

    private static final Instant NOW = Instant.parse("2026-11-08T00:00:00Z");
    private static final java.util.concurrent.Executor DIRECT = Runnable::run;

    private final UUID runId = UUID.randomUUID();
    private final UUID consoleProject = UUID.randomUUID();
    private final UUID researchId = UUID.randomUUID();
    private final ResearchBridge bridge = mock(ResearchBridge.class);
    private final ResearchProjectReadPort projects = mock(ResearchProjectReadPort.class);
    private final ExecutionRunRepository runs = mock(ExecutionRunRepository.class);

    private ExecutionRun run() {
        return new ExecutionRun(runId, consoleProject, 1, RunStatus.RUNNING, 4, null, 0, null, NOW, null, null, 0, null, null);
    }

    private static BridgeEvent event(int seq) {
        return new BridgeEvent(seq, NOW.toString(), "step", Map.of("status", "RETRYING"));
    }

    /** 以真的 RunConsumers 跑一則事件，記錄 commit、notify、publish 三者的先後。 */
    private List<String> runOneEvent(boolean healingRelevant) {
        List<String> order = new CopyOnWriteArrayList<>();
        AgentBridge agentBridge = mock(AgentBridge.class);
        RunEventProcessor processor = mock(RunEventProcessor.class);
        RuntimeSettings settings = mock(RuntimeSettings.class);
        PlatformTransactionManager transactions = mock(PlatformTransactionManager.class);
        ResearchHealingNotifier notifier = mock(ResearchHealingNotifier.class);
        when(settings.consumerBackoffInitial()).thenReturn(Duration.ofMillis(5));
        when(settings.consumerBackoffMax()).thenReturn(Duration.ofMillis(20));
        when(settings.consumerIdleTimeout()).thenReturn(Duration.ofSeconds(45));
        doAnswer(inv -> {
            order.add("commit");
            return null;
        }).when(transactions).commit(any());
        doAnswer(inv -> {
            order.add("notify");
            return null;
        }).when(notifier).notify(runId);
        when(processor.process(eq(runId), any())).thenReturn(
                new Outcome(List.of(new Frame(Kind.LOGS, 1, 0, "log", "m1")), List.of(), true, healingRelevant));
        doAnswer((Answer<Object>) inv -> {
            Consumer<BridgeEvent> handler = inv.getArgument(3);
            handler.accept(event(1));
            return null;
        }).when(agentBridge).streamEvents(eq(runId), anyInt(), any(), any());
        RunEventHub hub = new RunEventHub();
        hub.subscribe(runId, new RunEventHub.Listener() {
            @Override
            public void accept(Frame frame) {
                order.add("publish");
            }

            @Override
            public void runEnded() {
                // 結束通知不屬於本測試要記錄的三個步驟
            }
        });
        RunConsumers consumers = new RunConsumers(agentBridge, runs, processor, hub, new RunRegistry(), settings, transactions,
                Clock.fixed(NOW, ZoneOffset.UTC), notifier);
        try {
            consumers.start(runId, 0);
            assertThat(consumers.awaitIdle(Duration.ofSeconds(5))).isTrue();
        } finally {
            consumers.stopAll();
        }
        return order;
    }

    @Test
    void AT_962_9_6_aHealingRelevantEventNotifiesExactlyOnceBetweenTheCommitAndThePublish() {
        assertThat(runOneEvent(true)).as("順序固定：commit → notify → publish").containsExactly("commit", "notify", "publish");
    }

    @Test
    void AT_962_9_6_anIrrelevantEventNeverNotifies() {
        assertThat(runOneEvent(false)).as("無關事件：不通知").containsExactly("commit", "publish");
    }

    @Test
    void AT_962_9_6_onlyRetryingFailedAndEscalatedEventsAreFlaggedByTheProcessorOutcome() {
        assertThat(new Outcome(List.of(), List.of(), false).healingRelevant()).as("三參數建構子＝不相關").isFalse();
        assertThat(new Outcome(List.of(), List.of(), false, true).healingRelevant()).isTrue();
    }

    @Test
    void AT_962_9_E_1_anUnreachableBridgeOnlyLogsAWarningAndLeaksNoException() {
        when(runs.findById(runId)).thenReturn(Optional.of(run()));
        when(projects.researchIdOfConsoleProject(consoleProject)).thenReturn(Optional.of(researchId));
        when(bridge.healingSync(eq(researchId), any())).thenThrow(ResearchBridgeException.unreachable("連不上", false));
        ResearchHealingNotifier notifier = new ResearchHealingNotifier(bridge, projects, runs, DIRECT);
        Logger logger = (Logger) LoggerFactory.getLogger(ResearchHealingNotifier.class);
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.start();
        logger.addAppender(appender);
        try {
            assertThatCode(() -> notifier.notify(runId)).doesNotThrowAnyException();
        } finally {
            logger.detachAppender(appender);
        }
        verify(bridge, times(1)).healingSync(eq(researchId), any());
        assertThat(notifier.latest(researchId)).as("失敗不留快取").isEmpty();
        assertThat(appender.list).filteredOn(e -> e.getLevel() == Level.WARN).hasSize(1);
        assertThat(appender.list.get(0).getFormattedMessage()).doesNotContain("token");
    }

    @Test
    void AT_962_9_E_2_aRunOfANonResearchProjectIsANoOpWithZeroBridgeRequests() {
        when(runs.findById(runId)).thenReturn(Optional.of(run()));
        when(projects.researchIdOfConsoleProject(consoleProject)).thenReturn(Optional.empty());
        ResearchHealingNotifier notifier = new ResearchHealingNotifier(bridge, projects, runs, DIRECT);

        assertThatCode(() -> notifier.notify(runId)).doesNotThrowAnyException();

        verify(bridge, never()).healingSync(any(), any());
    }

    @Test
    void aSuccessfulSyncIsCachedInMemoryForTheHealingEndpoint() {
        when(runs.findById(runId)).thenReturn(Optional.of(run()));
        when(projects.researchIdOfConsoleProject(consoleProject)).thenReturn(Optional.of(researchId));
        when(bridge.healingSync(eq(researchId), any())).thenReturn(Map.of("view_rows", 5, "log_lines", 3, "appended", 1,
                "spec_change", List.of(Map.of("path", "docs/a.md", "expected", "x", "actual", "y"))));
        ResearchHealingNotifier notifier = new ResearchHealingNotifier(bridge, projects, runs, DIRECT);

        notifier.notify(runId);

        assertThat(notifier.latest(researchId)).hasValueSatisfying(s -> {
            assertThat(s.viewRows()).isEqualTo(5);
            assertThat(s.logLines()).isEqualTo(3);
            assertThat(s.specChangePaths()).containsExactly("docs/a.md");
        });
    }
}
