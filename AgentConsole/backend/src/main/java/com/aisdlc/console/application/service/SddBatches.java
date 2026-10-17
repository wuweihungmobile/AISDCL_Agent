package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.PassCriteriaSpecReader;
import com.aisdlc.console.application.port.out.RuntimeSettings;
import com.aisdlc.console.domain.model.execution.SddTaskSpec;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.service.ExecutionPlanner.Plan;
import com.aisdlc.console.domain.service.ExecutionPlanner.PlannedTask;
import com.aisdlc.console.domain.service.SddBatchPolicy;
import com.aisdlc.console.domain.service.SddBatchPolicy.Decision;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

/**
 * SDD 批次的準備（契約 §1.10.5、§1.10.6）：execute 與審核決定開的後續批次<b>共用</b>——兩者都對本批次範圍內的任務做同一個資格判定
 * （{@link SddBatchPolicy}）。資格成立時，計畫的 step_id 換成任務 {@code passCriteriaSpec.stepId}（{@code dag.nodes[].stepId} 同步），
 * 簽核人取範圍內任務的 {@code signedOffBy}（全空取 {@code actor}，所以永遠是具名人）；不成立時計畫原樣、依判定出聲。
 */
@Component
public class SddBatches {

    /**
     * @param plan     資格成立時是 step_id 已改寫的計畫；否則是傳入的計畫
     * @param decision 判定（含警告、SDD 欄位）
     * @param approver 送給 Bridge 的簽核人；資格不成立為 null
     */
    public record Prepared(Plan plan, Decision decision, String approver) {
    }

    private final PassCriteriaSpecReader reader;
    private final RuntimeSettings runtime;

    public SddBatches(PassCriteriaSpecReader reader, RuntimeSettings runtime) {
        this.reader = reader;
        this.runtime = runtime;
    }

    public Prepared prepare(Project project, Plan plan, String actor) {
        Map<UUID, SddTaskSpec> specs = new LinkedHashMap<>();
        for (PlannedTask planned : plan.tasks()) {
            specs.put(planned.task().id(), reader.read(planned.task().passCriteriaSpec()));
        }
        Decision decision = SddBatchPolicy.decide(project.sddSpecDir() != null, runtime.sddWriteTokenConfigured(),
                plan.tasks(), specs);
        if (!decision.active()) {
            return new Prepared(plan, decision, null);
        }
        return new Prepared(plan.withStepIds(decision.stepIds()), decision,
                SddBatchPolicy.approverOf(plan.tasks(), actor));
    }
}
