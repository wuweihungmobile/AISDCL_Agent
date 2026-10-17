package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.RunStarted;
import com.aisdlc.console.application.port.out.AgentBridge.StartRunRequest;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.port.out.ExecutionStepRepository;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.ReviewRequestRepository;
import com.aisdlc.console.application.port.out.TaskRepository;
import com.aisdlc.console.application.service.ConfigMaterializer.Materialized;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.DagSnapshot;
import com.aisdlc.console.domain.model.execution.EngineCapabilities;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.ExecutionWarning;
import com.aisdlc.console.domain.model.execution.RunScope;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.service.ExecutionPlanner.Plan;
import com.aisdlc.console.domain.service.PlaybookBuilder.Playbook;
import com.aisdlc.console.domain.service.SddBatchPolicy;
import com.aisdlc.console.support.DomainFixtures;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.SimpleTransactionStatus;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static com.aisdlc.console.domain.model.execution.EngineCapabilityState.ENABLED;
import static com.aisdlc.console.domain.model.execution.EngineCapabilityState.OFF;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

/**
 * 建立批次時的物化只呼叫一次，而且在建列之前（契約 §3.4.2 一致性規則①；W7_OVERVIEW 裁決 D-11）。為什麼重要：落庫的
 * {@code engine_capabilities} 是前端看到的「這個批次實際送進引擎什麼」，它必須與 Bridge 請求<b>同源</b>——若建列時讀一次設定、
 * 組 Bridge 請求時又讀一次（v1.2 的寫法就是交易 1 之後才物化），兩次之間管理員改了金鑰或旗標，畫面上的能力就與引擎實際收到的設定
 * 不一致，而且沒有任何錯誤可以事後發現。用「第二次呼叫會回不同結果」的替身把這條規則釘成可失敗的測試。
 */
class RunLauncherTest {

    private final ExecutionRunRepository runs = mock(ExecutionRunRepository.class);
    private final ExecutionStepRepository steps = mock(ExecutionStepRepository.class);
    private final ProjectRepository projects = mock(ProjectRepository.class);
    private final TaskRepository tasks = mock(TaskRepository.class);
    private final ReviewRequestRepository reviews = mock(ReviewRequestRepository.class);
    private final AgentBridge bridge = mock(AgentBridge.class);
    private final ConfigMaterializer config = mock(ConfigMaterializer.class);
    private final RunConsumers consumers = mock(RunConsumers.class);
    private final BridgeHealthMonitor health = mock(BridgeHealthMonitor.class);
    private final PlatformTransactionManager transactions = mock(PlatformTransactionManager.class);
    private final Clock clock = Clock.fixed(Instant.parse("2026-10-16T08:00:00Z"), ZoneOffset.UTC);
    private RunLauncher launcher;
    private Project project;

    @BeforeEach
    void setUp() {
        project = DomainFixtures.project("launcher");
        when(transactions.getTransaction(any())).thenReturn(new SimpleTransactionStatus());
        when(projects.findByIdForUpdate(project.id())).thenReturn(Optional.of(project));
        when(runs.nextRunNumber(project.id())).thenReturn(1);
        when(runs.insert(any(ExecutionRun.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(tasks.findByIds(any())).thenReturn(List.of());
        when(reviews.findPendingOfOtherRuns(any(), any())).thenReturn(List.of());
        when(bridge.startRun(any(StartRunRequest.class))).thenAnswer(invocation -> new RunStarted(
                ((StartRunRequest) invocation.getArgument(0)).runId().toString(), BridgeStatus.RUNNING, null, null,
                "test-bridge"));
        launcher = new RunLauncher(runs, steps, projects, tasks, reviews, bridge, config, consumers, health,
                new RunRegistry(), transactions, clock);
    }

    private RunLauncher.Launch launch(int level) {
        return new RunLauncher.Launch(project, new Plan(List.of(), List.of(), DagSnapshot.EMPTY),
                new Playbook("launcher", "全部完成", 3, List.of()), RunScope.all(), level, 1000L);
    }

    private static Materialized materialized(String command, String key, EngineCapabilities capabilities) {
        return new Materialized(Map.of("claude", Map.of("command", command)), key == null ? Map.of()
                : Map.of("MINIMAX_API_KEY", key), capabilities);
    }

    @Test
    void materializesOnceBeforeTheRowAndFeedsRowAndRequest() {
        Materialized first = materialized("first", "key-one", new EngineCapabilities(ENABLED, ENABLED));
        Materialized second = materialized("second", null, new EngineCapabilities(OFF, OFF));
        // 若實作在別處又物化一次（例如回到「交易 1 之後才物化」），第二次呼叫會得到另一份設定：落庫與送出就會各說各話
        when(config.materialize(7)).thenReturn(first, second);

        ExecutionRun created = launcher.launch(launch(7), run -> { });

        verify(config, times(1)).materialize(anyInt());
        InOrder order = inOrder(config, runs, bridge);
        order.verify(config).materialize(7);
        order.verify(runs).insert(any(ExecutionRun.class));
        order.verify(bridge).startRun(any(StartRunRequest.class));
        ArgumentCaptor<ExecutionRun> inserted = ArgumentCaptor.forClass(ExecutionRun.class);
        verify(runs).insert(inserted.capture());
        ArgumentCaptor<StartRunRequest> request = ArgumentCaptor.forClass(StartRunRequest.class);
        verify(bridge).startRun(request.capture());
        assertThat(inserted.getValue().engineCapabilities()).as("落庫的能力狀態").isEqualTo(first.engineCapabilities());
        assertThat(created.engineCapabilities()).isEqualTo(first.engineCapabilities());
        assertThat(request.getValue().configOverrides()).as("送給 Bridge 的設定與落庫的能力同一次物化")
                .isSameAs(first.configOverrides());
        assertThat(request.getValue().env()).isSameAs(first.env());
        assertThat(request.getValue().runId()).isEqualTo(inserted.getValue().id());
    }

    @Test
    void theAutonomyLevelOfTheLaunchIsWhatTheMaterializationIsAskedFor() {
        when(config.materialize(10)).thenReturn(materialized("c", "k", new EngineCapabilities(ENABLED, ENABLED)));

        launcher.launch(launch(10), run -> { });

        verify(config).materialize(10);
        verify(config, times(1)).materialize(anyInt());
    }

    @Test
    void aFailedMaterializationHappensBeforeAnyRowExists() {
        when(config.materialize(3)).thenThrow(new IllegalStateException("系統參數不存在：model.apiKey"));

        assertThatThrownBy(() -> launcher.launch(launch(3), run -> { })).isInstanceOf(IllegalStateException.class);

        verifyNoInteractions(runs, bridge, consumers, health);
    }

    // ── v1.5：SDD 批次（契約 §1.10.6、§3.4.1）──────────────────────────────────────────────

    private RunLauncher.Launch sddLaunch(Project bound, SddBatchPolicy.Decision decision, String approver) {
        return new RunLauncher.Launch(bound, new Plan(List.of(), List.of(), DagSnapshot.EMPTY),
                new Playbook("launcher", "全部完成", 3, List.of()), RunScope.all(), 4, 1000L, decision, approver);
    }

    private static final SddBatchPolicy.Decision ACTIVE = new SddBatchPolicy.Decision(true, null, Map.of(), Map.of());

    private StartRunRequest sentRequest() {
        ArgumentCaptor<StartRunRequest> request = ArgumentCaptor.forClass(StartRunRequest.class);
        verify(bridge).startRun(request.capture());
        return request.getValue();
    }

    @Test
    void anActiveSddDecisionSendsTheBlockBuiltFromTheProjectsBinding() {
        Project bound = DomainFixtures.boundProject("bound", "/work/bound", "my-key", "/work/bound/docs",
                "/work/bound/docs/TCS-A.md");
        when(projects.findByIdForUpdate(bound.id())).thenReturn(Optional.of(bound));
        when(runs.nextRunNumber(bound.id())).thenReturn(1);
        when(config.materialize(4)).thenReturn(materialized("c", null, new EngineCapabilities(OFF, OFF)));

        launcher.launch(sddLaunch(bound, ACTIVE, "approver-1"), run -> { });

        assertThat(sentRequest().sdd()).isEqualTo(new AgentBridge.SddBlock("/work/bound/docs", "/work/bound/docs/TCS-A.md",
                "my-key", "/work/bound", "approver-1"));
    }

    @Test
    void theEffectiveFsmProjectIsTheProjectNameWhenNothingIsBound() {
        Project named = DomainFixtures.boundProject("My Project 專案", "/work/named", null, "/work/named/docs", null);
        when(projects.findByIdForUpdate(named.id())).thenReturn(Optional.of(named));
        when(runs.nextRunNumber(named.id())).thenReturn(1);
        when(config.materialize(4)).thenReturn(materialized("c", null, new EngineCapabilities(OFF, OFF)));

        launcher.launch(sddLaunch(named, ACTIVE, "someone"), run -> { });

        AgentBridge.SddBlock block = sentRequest().sdd();
        assertThat(block.fsmProject()).as("原名原樣，Backend 不淨化").isEqualTo("My Project 專案");
        assertThat(block.specFile()).isNull();
        assertThat(block.root()).isEqualTo("/work/named");
    }

    @Test
    void aLaunchWithoutAnActiveDecisionSendsNoSddBlockAtAll() {
        when(config.materialize(4)).thenReturn(materialized("c", null, new EngineCapabilities(OFF, OFF)));
        SddBatchPolicy.Decision inactive = new SddBatchPolicy.Decision(false,
                ExecutionWarning.inactive(ExecutionWarning.MIXED_SCOPE, "混合"), Map.of(), Map.of());

        launcher.launch(sddLaunch(project, inactive, null), run -> { });

        assertThat(sentRequest().sdd()).isNull();
    }

    @Test
    void theInactiveWarningComesFirstThenTheBridgesOwnWarningsVerbatim() {
        when(config.materialize(4)).thenReturn(materialized("c", null, new EngineCapabilities(OFF, OFF)));
        ExecutionWarning bridgeWarning = new ExecutionWarning(ExecutionWarning.FROZEN_DIGEST_ABSENT, null, "舊狀態檔");
        when(bridge.startRun(any(StartRunRequest.class))).thenAnswer(invocation -> new RunStarted(
                ((StartRunRequest) invocation.getArgument(0)).runId().toString(), BridgeStatus.RUNNING, null, null,
                "test-bridge", List.of(bridgeWarning)));
        ExecutionWarning inactiveWarning = ExecutionWarning.inactive(ExecutionWarning.NOT_BOUND, "尚未綁定");

        RunLauncher.Launched launched = launcher.launchWithWarnings(sddLaunch(project,
                new SddBatchPolicy.Decision(false, inactiveWarning, Map.of(), Map.of()), null), run -> { });

        assertThat(launched.warnings()).containsExactly(inactiveWarning, bridgeWarning);
        assertThat(launched.run().projectId()).isEqualTo(project.id());
    }

    @Test
    void aLaunchWithoutAnyWarningReturnsAnEmptyListNotNull() {
        when(config.materialize(4)).thenReturn(materialized("c", null, new EngineCapabilities(OFF, OFF)));

        RunLauncher.Launched launched = launcher.launchWithWarnings(sddLaunch(project, SddBatchPolicy.Decision.NONE, null),
                run -> { });

        assertThat(launched.warnings()).isEmpty();
    }

    @Test
    void aBridgeSddRefusalIsTranslatedAndTheRowCompensated() {
        Project bound = DomainFixtures.boundProject("bound", "/work/bound", null, "/work/bound/docs", null);
        when(projects.findByIdForUpdate(bound.id())).thenReturn(Optional.of(bound));
        when(runs.nextRunNumber(bound.id())).thenReturn(1);
        when(config.materialize(4)).thenReturn(materialized("c", null, new EngineCapabilities(OFF, OFF)));
        when(bridge.startRun(any(StartRunRequest.class))).thenThrow(new AgentBridge.BridgeRejectedException(404,
                "fsm_not_found", null, null, List.of(), Map.of("code", 404, "reason", "fsm_not_found")));

        assertThatThrownBy(() -> launcher.launch(sddLaunch(bound, ACTIVE, "approver"), run -> { }))
                .isInstanceOfSatisfying(com.aisdlc.console.domain.exception.ConflictException.class, e -> {
                    assertThat(e.reason()).isEqualTo("sdd_fsm_not_found");
                    assertThat(e.details()).containsEntry("sddProject", "bound");
                });
        verify(runs).deleteById(any());
        verifyNoInteractions(consumers);
    }
}
