package com.aisdlc.console.domain.model.execution;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Bridge 的八態折成 Console 的六態、狀態字串的容錯解析，以及批次範圍的預設。為什麼重要：PAUSING／CANCELLING 只是過渡態，
 * 若原樣寫進 DB 會違反 {@code execution_runs.status} 的 CHECK；Bridge 回了不認得的狀態字串（版本差異）時不能丟例外讓整條事件消費停擺。
 */
class BridgeStatusAndScopeTest {

    @Test
    void transitionalStatesFoldBackToRunningAndEveryOtherStateKeepsItsName() {
        assertThat(BridgeStatus.PAUSING.fold()).isEqualTo(RunStatus.RUNNING);
        assertThat(BridgeStatus.CANCELLING.fold()).isEqualTo(RunStatus.RUNNING);
        for (BridgeStatus status : BridgeStatus.values()) {
            if (status != BridgeStatus.PAUSING && status != BridgeStatus.CANCELLING) {
                assertThat(status.fold().name()).isEqualTo(status.name());
            }
        }
    }

    @Test
    void onlyCompletedFailedAndCancelledAreTerminal() {
        for (BridgeStatus status : BridgeStatus.values()) {
            boolean expected = status == BridgeStatus.COMPLETED || status == BridgeStatus.FAILED
                    || status == BridgeStatus.CANCELLED;
            assertThat(status.terminal()).as(status.name()).isEqualTo(expected);
        }
    }

    @Test
    void parsingToleratesCaseAndWhitespaceAndReturnsEmptyForAnythingUnknown() {
        assertThat(BridgeStatus.parse("running")).contains(BridgeStatus.RUNNING);
        assertThat(BridgeStatus.parse("  Paused ")).contains(BridgeStatus.PAUSED);
        assertThat(BridgeStatus.parse("CANCELLING")).contains(BridgeStatus.CANCELLING);
        assertThat(BridgeStatus.parse("weird")).isEqualTo(Optional.empty());
        assertThat(BridgeStatus.parse("")).isEmpty();
        assertThat(BridgeStatus.parse(null)).isEmpty();
    }

    @Test
    void aScopeDefaultsToAllWithNoLimitsAndCopiesItsListsDefensively() {
        RunScope empty = new RunScope(null, null, null, null, null);
        assertThat(empty.mode()).isEqualTo(ScopeMode.ALL);
        assertThat(empty.goalIds()).isEmpty();
        assertThat(empty.taskIds()).isEmpty();
        assertThat(empty.limits()).isEqualTo(RunLimits.NONE);
        assertThat(empty.followUpOfRunId()).isNull();
        assertThat(RunScope.all()).isEqualTo(empty);

        UUID goal = UUID.randomUUID();
        List<UUID> goals = new ArrayList<>(List.of(goal));
        RunScope selected = new RunScope(ScopeMode.SELECTED, goals, List.of(), RunLimits.NONE, null);
        goals.add(UUID.randomUUID());
        assertThat(selected.goalIds()).as("建立後改原清單不影響範圍").containsExactly(goal);
        assertThatThrownBy(() -> selected.goalIds().add(UUID.randomUUID())).isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void aFollowUpScopePointsAtItsOriginalRunAndKeepsEverythingElse() {
        UUID goal = UUID.randomUUID();
        UUID original = UUID.randomUUID();
        RunScope base = new RunScope(ScopeMode.SELECTED, List.of(goal), List.of(), RunLimits.NONE, null);

        RunScope followUp = base.withFollowUpOf(original);

        assertThat(followUp.followUpOfRunId()).isEqualTo(original);
        assertThat(followUp.mode()).isEqualTo(ScopeMode.SELECTED);
        assertThat(followUp.goalIds()).containsExactly(goal);
        assertThat(base.followUpOfRunId()).as("原範圍不變").isNull();
    }
}
