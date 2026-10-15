package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.execution.DagSnapshot;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Node;
import com.aisdlc.console.domain.model.execution.DagSnapshot.NodeKind;
import com.aisdlc.console.domain.model.execution.ReviewDecision;
import com.aisdlc.console.domain.model.execution.ReviewKind;
import com.aisdlc.console.domain.service.ReviewGatePolicy.GateReview;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 自治等級的審核閘決策表（契約 §3.6.1／§3.6.2）。夾具是 PRJ-A 的形狀：G1（步驟 1、2）→ G2（步驟 3），共 3 步。
 * 「提前一步」的 WHY：{@code :pause} 在呼叫之後的下一個步驟邊界才生效，所以要在步驟 i 之後停，就得在步驟 i 剛開始時呼叫。
 */
class ReviewGatePolicyTest {

    private static final UUID G1 = UUID.randomUUID();
    private static final UUID G2 = UUID.randomUUID();

    private static DagSnapshot prjA() {
        List<Node> nodes = new ArrayList<>();
        nodes.add(new Node(G1, NodeKind.GOAL, "基礎", null, null, 1));
        nodes.add(new Node(UUID.randomUUID(), NodeKind.TASK, "T1", G1, "G1-T1", 1));
        nodes.add(new Node(UUID.randomUUID(), NodeKind.TASK, "T2", G1, "G1-T2", 2));
        nodes.add(new Node(G2, NodeKind.GOAL, "核心", null, null, 2));
        nodes.add(new Node(UUID.randomUUID(), NodeKind.TASK, "T3", G2, "G2-T1", 3));
        return new DagSnapshot(nodes, List.of());
    }

    /** 等級 × 剛開始的步驟位置 → 是否呼叫 :pause（總步數 3）。 */
    @ParameterizedTest(name = "等級 {0}、步驟 {1} 開始 → pause={2}")
    @CsvSource({
            "1,1,true", "1,2,true", "1,3,false",
            "2,1,false", "2,2,true", "2,3,false",
            "3,1,false", "3,2,true", "3,3,false",
            "4,1,false", "4,2,false", "4,3,false",
            "5,2,false", "6,2,false", "10,2,false"})
    void theStartOfAStepDecidesWhetherToPause(int level, int position, boolean pause) {
        assertThat(ReviewGatePolicy.shouldPauseAtStart(level, position, 3, prjA())).isEqualTo(pause);
    }

    @Test
    void theLastStepNeverPausesBecauseTheRunCompletesDirectly() {
        for (int level = 1; level <= 10; level++) {
            assertThat(ReviewGatePolicy.shouldPauseAtStart(level, 3, 3, prjA())).as("等級 " + level).isFalse();
        }
    }

    @Test
    void level1AsksToConfirmTheNextTaskAfterEveryStep() {
        assertThat(ReviewGatePolicy.reviewOnPause(1, 1, 3, prjA())).contains(
                new GateReview(ReviewKind.TASK_CONFIRM, 2, 1, false));
        assertThat(ReviewGatePolicy.reviewOnPause(1, 2, 3, prjA())).contains(
                new GateReview(ReviewKind.TASK_CONFIRM, 3, 2, false));
    }

    @Test
    void level2AsksToConfirmTheNextGoalAtAGoalBoundaryAndDegradesToATaskConfirmWhenThePauseLandedLate() {
        assertThat(ReviewGatePolicy.reviewOnPause(2, 2, 3, prjA())).contains(
                new GateReview(ReviewKind.GOAL_CONFIRM, 3, 2, false));
        // 暫停比預期晚一步，停在目標內部（只完成 1 步）：降級為 TASK_CONFIRM 並標記要加註
        assertThat(ReviewGatePolicy.reviewOnPause(2, 1, 3, prjA())).contains(
                new GateReview(ReviewKind.TASK_CONFIRM, 2, 1, true));
    }

    @Test
    void level3ReviewsTheJustFinishedGoalWithItsLastTaskAsSubject() {
        assertThat(ReviewGatePolicy.reviewOnPause(3, 2, 3, prjA())).contains(
                new GateReview(ReviewKind.GOAL_COMPLETED, 2, 2, false));
        assertThat(ReviewGatePolicy.reviewOnPause(3, 1, 3, prjA())).contains(
                new GateReview(ReviewKind.TASK_CONFIRM, 2, 1, true));
    }

    @Test
    void noReviewForLevelsFourAndUpOrWhenThereIsNothingLeftToConfirm() {
        for (int level = 4; level <= 10; level++) {
            assertThat(ReviewGatePolicy.reviewOnPause(level, 1, 3, prjA())).as("等級 " + level).isEmpty();
        }
        assertThat(ReviewGatePolicy.reviewOnPause(1, 3, 3, prjA())).isEqualTo(Optional.empty());
        assertThat(ReviewGatePolicy.reviewOnPause(1, 0, 3, prjA())).isEqualTo(Optional.empty());
    }

    /** 失敗時建不建審核項：等級 1～4 只有升級（ESCALATION）；等級 ≥5 任何失敗都建。 */
    @ParameterizedTest(name = "等級 {0}、升級={1} → 建審核項={2}")
    @CsvSource({
            "1,true,true", "1,false,false", "3,false,false", "4,true,true", "4,false,false",
            "5,true,true", "5,false,true", "6,false,true", "10,false,true"})
    void failuresCreateAReviewByLevel(int level, boolean escalation, boolean creates) {
        assertThat(ReviewGatePolicy.createsReviewOnFailure(level, escalation)).isEqualTo(creates);
    }

    @Test
    void allowedDecisionsFollowTheKindInTheContractsOrder() {
        assertThat(ReviewGatePolicy.allowedDecisions(ReviewKind.TASK_CONFIRM, true))
                .containsExactly(ReviewDecision.APPROVE, ReviewDecision.REJECT);
        assertThat(ReviewGatePolicy.allowedDecisions(ReviewKind.GOAL_CONFIRM, true))
                .containsExactly(ReviewDecision.APPROVE, ReviewDecision.REJECT);
        assertThat(ReviewGatePolicy.allowedDecisions(ReviewKind.GOAL_COMPLETED, true))
                .containsExactly(ReviewDecision.APPROVE, ReviewDecision.REJECT, ReviewDecision.RETRY);
        assertThat(ReviewGatePolicy.allowedDecisions(ReviewKind.ESCALATED, true))
                .containsExactly(ReviewDecision.RETRY, ReviewDecision.SKIP, ReviewDecision.REJECT);
        assertThat(ReviewGatePolicy.allowedDecisions(ReviewKind.ESCALATED, false))
                .containsExactly(ReviewDecision.RETRY, ReviewDecision.REJECT);
    }

    @Test
    void everyDecisionMapsToItsOwnTerminalReviewStatus() {
        assertThat(ReviewDecision.APPROVE.resultingStatus().name()).isEqualTo("APPROVED");
        assertThat(ReviewDecision.REJECT.resultingStatus().name()).isEqualTo("REJECTED");
        assertThat(ReviewDecision.RETRY.resultingStatus().name()).isEqualTo("RETRIED");
        assertThat(ReviewDecision.SKIP.resultingStatus().name()).isEqualTo("SKIPPED");
    }
}
