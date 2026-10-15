package com.aisdlc.console.application.port.in;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.RunView;
import com.aisdlc.console.domain.model.execution.ReviewDecision;

import java.util.Optional;
import java.util.UUID;

/** 執行控制（契約 §1.2.4～§1.2.6、§1.2.10、§1.2.11）：pause／resume／cancel／restore 與審核決定。OPERATOR 以上。 */
public interface ExecutionControlUseCase {

    RunView pause(UUID runId, String actor);

    RunView resume(UUID runId, String actor);

    RunView cancel(UUID runId, String actor);

    RunView restore(UUID runId, UUID checkpointId, String actor);

    /**
     * 審核決定（{@code {reviewId}} 即路徑的 {@code {stepId}}）。{@code SKIP}、以及找不到還原點而改開後續批次的
     * {@code RETRY} 會另開後續批次，回傳其 id（放在回應標頭 {@code X-Follow-Up-Run-Id}）；其餘為 empty。
     */
    Optional<UUID> review(UUID runId, UUID reviewId, ReviewDecision decision, String comment, String actor);
}
