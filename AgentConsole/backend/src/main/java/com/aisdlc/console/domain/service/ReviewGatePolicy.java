package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.execution.DagSnapshot;
import com.aisdlc.console.domain.model.execution.ReviewDecision;
import com.aisdlc.console.domain.model.execution.ReviewKind;

import java.util.List;
import java.util.Optional;

/**
 * 自治等級的審核閘決策表（契約 §3.6；Architecture §6(c).c.4「提前一步」）。純 Java。
 *
 * <p>AutoClaude 沒有審核鉤子，閘點由 Console 計算、以 Bridge 的 {@code :pause} 實現。{@code :pause} 在「呼叫之後的下一個
 * 步驟邊界」生效，所以閘點一律提前一步：要在步驟 {@code i} 之後停，就在步驟 {@code i} 的 {@code STARTED}（第一次）時呼叫。
 */
public final class ReviewGatePolicy {

    private ReviewGatePolicy() {
    }

    /**
     * 閘點判定（§3.6.1）：步驟 {@code position}（1 起）剛開始時要不要呼叫 {@code :pause}。
     *
     * <ul>
     *   <li>等級 1（Manual Confirm）：{@code position < total}，每個任務之間都停；</li>
     *   <li>等級 2／3：{@code position} 是所屬目標的最後一步且 {@code position < total}（目標之間停）；</li>
     *   <li>等級 ≥ 4：不預先暫停（4＝只有升級時介入；5～10 同 5，等級 6～10 不另送引擎設定）。</li>
     * </ul>
     * 最後一個步驟（{@code position == total}）完成時 run 直接 COMPLETED，不暫停、不建審核項。
     */
    public static boolean shouldPauseAtStart(int autonomyLevel, int position, int total, DagSnapshot dag) {
        if (position >= total) {
            return false;
        }
        return switch (autonomyLevel) {
            case 1 -> true;
            case 2, 3 -> dag.isLastOfGoal(position);
            default -> false;
        };
    }

    /**
     * 審核項的決定（§3.6.2）：{@code kind}、審核項「主角」任務的步驟位置，以及是否因暫停點比預期晚一步而降級為
     * {@link ReviewKind#TASK_CONFIRM}（reason 要加註）。
     *
     * @param subjectPosition 取 goalId／taskId 的步驟位置：等級 1／2 是「下一個任務」，等級 3 是「剛完成目標的最後一個任務」
     * @param evidencePosition 佐證步驟列（{@code execution_steps} 的 COMPLETED 列）的步驟位置：剛完成的那一步
     */
    public record GateReview(ReviewKind kind, int subjectPosition, int evidencePosition, boolean degraded) {
    }

    /**
     * Run 進入 {@code PAUSED} 且是由閘點暫停造成時，依「實際位置」{@code completedSteps = k} 決定審核項（暫停可能比預期晚一步，
     * 見 Architecture §12 L-7）：等級 1 照常 TASK_CONFIRM；等級 2／3 若 {@code k} 不是目標邊界則降級為 TASK_CONFIRM。
     * 已經沒有下一步（{@code k >= total}）或等級 ≥ 4 時沒有審核項。
     */
    public static Optional<GateReview> reviewOnPause(int autonomyLevel, int completedSteps, int total,
                                                      DagSnapshot dag) {
        int k = completedSteps;
        if (k < 1 || k >= total) {
            return Optional.empty();
        }
        return switch (autonomyLevel) {
            case 1 -> Optional.of(new GateReview(ReviewKind.TASK_CONFIRM, k + 1, k, false));
            case 2 -> dag.isLastOfGoal(k)
                    ? Optional.of(new GateReview(ReviewKind.GOAL_CONFIRM, k + 1, k, false))
                    : Optional.of(new GateReview(ReviewKind.TASK_CONFIRM, k + 1, k, true));
            case 3 -> dag.isLastOfGoal(k)
                    ? Optional.of(new GateReview(ReviewKind.GOAL_COMPLETED, k, k, false))
                    : Optional.of(new GateReview(ReviewKind.TASK_CONFIRM, k + 1, k, true));
            default -> Optional.empty();
        };
    }

    /**
     * Run 進入 {@code FAILED} 時是否建審核項（§3.6.2）：等級 1～4 只在「引擎升級（ESCALATION）」時；等級 ≥ 5 任何失敗都建
     * （引擎沒有「替代方案」能力，Console 行為與 4 相同，只是任何失敗都會有審核項）。
     */
    public static boolean createsReviewOnFailure(int autonomyLevel, boolean escalation) {
        return escalation || autonomyLevel >= 5;
    }

    /** 各 kind 允許的決定（{@code ReviewRequestResponse.allowedDecisions}；順序固定，E2E 逐一比對）。 */
    public static List<ReviewDecision> allowedDecisions(ReviewKind kind, boolean hasTask) {
        return switch (kind) {
            case TASK_CONFIRM, GOAL_CONFIRM -> List.of(ReviewDecision.APPROVE, ReviewDecision.REJECT);
            case GOAL_COMPLETED -> List.of(ReviewDecision.APPROVE, ReviewDecision.REJECT, ReviewDecision.RETRY);
            case ESCALATED -> hasTask
                    ? List.of(ReviewDecision.RETRY, ReviewDecision.SKIP, ReviewDecision.REJECT)
                    : List.of(ReviewDecision.RETRY, ReviewDecision.REJECT);
        };
    }
}
