package com.aisdlc.console.application.service;

import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.RunStatus;
import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 批次列表 {@code bridgeStatus} 的決定規則（契約 §1.2.2，C-11）。為什麼重要：列表不逐批呼叫 Bridge，所以這個欄位只能由
 * 「記憶體內最近一則 status 事件」與「DB 六態」推得；規則錯了，前端要顯示的 PAUSING／CANCELLING 晶片就會消失，或更糟——
 * 同一列出現 status 與 bridgeStatus 互相矛盾的組合（已完成卻顯示執行中）。
 */
class ExecutionQueryServiceTest {

    @Test
    void aRunningRunTakesTheTransitionStateTheConsumerLastSawWhenItAgreesWithTheDatabase() {
        for (BridgeStatus known : new BridgeStatus[] {BridgeStatus.RUNNING, BridgeStatus.PAUSING,
                BridgeStatus.CANCELLING}) {
            assertThat(ExecutionQueryService.listBridgeStatus(RunStatus.RUNNING, known)).as(known.name())
                    .isEqualTo(known);
        }
    }

    @Test
    void aRunningRunWithNothingInMemoryHasNoBridgeStatusBecauseRunningPausingAndCancellingCannotBeToldApart() {
        assertThat(ExecutionQueryService.listBridgeStatus(RunStatus.RUNNING, null)).isNull();
    }

    @Test
    void everyOtherDatabaseStatusFallsBackToTheSameNamedBridgeStatusWhenMemoryHasNothing() {
        for (RunStatus status : RunStatus.values()) {
            if (status == RunStatus.RUNNING) {
                continue;
            }
            assertThat(ExecutionQueryService.listBridgeStatus(status, null)).as(status.name())
                    .isEqualTo(BridgeStatus.valueOf(status.name()));
        }
    }

    @Test
    void aStaleMemoryValueThatContradictsTheDatabaseIsIgnored() {
        // DB 已先一步寫了終態／PAUSED，事件還沒消費到：不可出現「status=COMPLETED、bridgeStatus=RUNNING」
        assertThat(ExecutionQueryService.listBridgeStatus(RunStatus.COMPLETED, BridgeStatus.RUNNING))
                .isEqualTo(BridgeStatus.COMPLETED);
        assertThat(ExecutionQueryService.listBridgeStatus(RunStatus.CANCELLED, BridgeStatus.CANCELLING))
                .isEqualTo(BridgeStatus.CANCELLED);
        assertThat(ExecutionQueryService.listBridgeStatus(RunStatus.PAUSED, BridgeStatus.PAUSING))
                .isEqualTo(BridgeStatus.PAUSED);
        // 反方向：DB 還是 RUNNING，記憶體卻是別的態（不可能折疊成 RUNNING）→ 當作沒有記憶體值
        assertThat(ExecutionQueryService.listBridgeStatus(RunStatus.RUNNING, BridgeStatus.PAUSED)).isNull();
    }

    @Test
    void aSettledMemoryValueEqualToTheDatabaseIsKeptAsIs() {
        assertThat(ExecutionQueryService.listBridgeStatus(RunStatus.PAUSED, BridgeStatus.PAUSED))
                .isEqualTo(BridgeStatus.PAUSED);
        assertThat(ExecutionQueryService.listBridgeStatus(RunStatus.COMPLETED, BridgeStatus.COMPLETED))
                .isEqualTo(BridgeStatus.COMPLETED);
    }

    @Test
    void theRegistryReportsTheLastSeenStatusOfARunAndNothingForAnUnknownOrForgottenOne() {
        RunRegistry registry = new RunRegistry();
        UUID run = UUID.randomUUID();
        assertThat(registry.knownBridgeStatus(run)).as("沒看過這個 run").isNull();

        registry.runtime(run).bridgeStatus = BridgeStatus.PAUSING;

        assertThat(registry.knownBridgeStatus(run)).isEqualTo(BridgeStatus.PAUSING);
        assertThat(registry.knownBridgeStatus(UUID.randomUUID())).as("別的 run 不受影響").isNull();
        registry.forget(run);
        assertThat(registry.knownBridgeStatus(run)).as("console-api 重啟後記憶體是空的").isNull();
    }
}
