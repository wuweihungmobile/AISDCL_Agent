package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionControlUseCase;
import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.RunView;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.domain.model.execution.ReviewDecision;
import org.springframework.stereotype.Service;

import java.util.Optional;
import java.util.UUID;

/**
 * {@link ExecutionControlUseCase} 的入口：把 pause／resume／cancel／restore（{@link ExecutionControlService}）與審核決定
 * （{@link ReviewService}）收在一處，並為每個寫入操作補上審計標註（{@code action}／{@code entity}，契約 §0.4 第 5 點）。
 * 交易邊界在下層（Bridge 呼叫不可放在資料庫交易內）。
 */
@Service
public class ExecutionOperations implements ExecutionControlUseCase {

    private final ExecutionControlService control;
    private final ReviewService reviewService;
    private final AuditTrail audit;

    public ExecutionOperations(ExecutionControlService control, ReviewService reviewService, AuditTrail audit) {
        this.control = control;
        this.reviewService = reviewService;
        this.audit = audit;
    }

    @Override
    public RunView pause(UUID runId, String actor) {
        audit.note("execution.pause", "execution", runId.toString());
        return control.pause(runId);
    }

    @Override
    public RunView resume(UUID runId, String actor) {
        audit.note("execution.resume", "execution", runId.toString());
        return control.resume(runId, actor);
    }

    @Override
    public RunView cancel(UUID runId, String actor) {
        audit.note("execution.cancel", "execution", runId.toString());
        return control.cancel(runId);
    }

    @Override
    public RunView restore(UUID runId, UUID checkpointId, String actor) {
        audit.note("execution.restore", "execution", runId.toString());
        return control.restore(runId, checkpointId, actor);
    }

    @Override
    public Optional<UUID> review(UUID runId, UUID reviewId, ReviewDecision decision, String comment, String actor) {
        audit.note("execution.review." + decision.name(), "execution", runId.toString());
        return reviewService.decide(runId, reviewId, decision, comment, actor);
    }
}
