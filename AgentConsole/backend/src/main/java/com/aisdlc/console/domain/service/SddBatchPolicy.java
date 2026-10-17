package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.execution.ExecutionWarning;
import com.aisdlc.console.domain.model.execution.SddTaskSpec;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.service.ExecutionPlanner.PlannedTask;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * SDD 批次資格判定（契約 §1.10.5；D-115-06）。純 Java：以本批次<b>範圍內</b>的任務為準，<b>全部成立</b>才送 {@code sdd} 區塊，任一不成立＝不送、
 * 走既有的 {@code G<g>-T<t>} 路徑並出聲（{@code sdd_governance_inactive} 警告）。
 *
 * <p>五項資格依序判定、回第一個不成立的 {@code cause}：①專案已有規格綁定（{@code not_bound}）②backend 已設定寫入權杖
 * （{@code token_not_configured}）③範圍內每個任務都是 SDD 來源且 {@code stepId}、{@code specDigest} 皆非空（{@code mixed_scope}）
 * ④所有任務的 {@code specDigest} 相等（{@code spec_mismatch}）⑤各任務的 {@code stepId} 互不相同（{@code duplicate_step_id}）。
 * <b>只有範圍內至少有一個 SDD 來源任務時才出聲</b>：沒有任何 SDD 來源任務的批次（一般手動專案）不帶警告。
 */
public final class SddBatchPolicy {

    private SddBatchPolicy() {
    }

    /**
     * 判定結果。
     *
     * @param active  true＝送 {@code sdd} 區塊並用 SDD step_id
     * @param warning {@code active=false} 且範圍內有 SDD 來源任務時的警告；其餘為 null
     * @param stepIds {@code active=true} 時：任務 id → 要用的 step_id（取自 {@code passCriteriaSpec.stepId}）；其餘為空
     * @param specs   {@code active=true} 時：任務 id → 要放進 playbook 的 SDD 欄位；其餘為空
     */
    public record Decision(boolean active, ExecutionWarning warning, Map<UUID, String> stepIds,
                           Map<UUID, SddTaskSpec> specs) {

        /** 不啟用、也不出聲（範圍內沒有任何 SDD 來源任務）。 */
        public static final Decision NONE = new Decision(false, null, Map.of(), Map.of());

        public Decision {
            stepIds = Map.copyOf(stepIds);
            specs = Map.copyOf(specs);
        }

        static Decision inactive(String cause, String detail) {
            return new Decision(false, ExecutionWarning.inactive(cause, detail), Map.of(), Map.of());
        }
    }

    /**
     * @param bound           專案已有規格綁定（{@code sddSpecDir} 非空）
     * @param tokenConfigured backend 已設定 SDD 寫入權杖
     * @param tasks           本批次展平後的步驟（依位置排序）
     * @param specs           任務 id → 它的 {@link SddTaskSpec}（沒有的視為 {@link SddTaskSpec#NONE}）
     */
    public static Decision decide(boolean bound, boolean tokenConfigured, List<PlannedTask> tasks,
                                  Map<UUID, SddTaskSpec> specs) {
        List<SddTaskSpec> ordered = new ArrayList<>();
        for (PlannedTask planned : tasks) {
            ordered.add(specs.getOrDefault(planned.task().id(), SddTaskSpec.NONE));
        }
        if (ordered.stream().noneMatch(SddTaskSpec::sddSource)) {
            return Decision.NONE;
        }
        if (!bound) {
            return Decision.inactive(ExecutionWarning.NOT_BOUND,
                    "專案尚未綁定 SDD 規格（sddSpecDir 為空，亦即還沒有用路徑 A 匯入過規格）；本批次沒有啟用 SDD 治理："
                            + "沒有預檢、沒有 FSM 同步、step_id 維持 G<g>-T<t>、事後也不會有追溯報告。請先以路徑 A 匯入規格（可併入此專案）");
        }
        if (!tokenConfigured) {
            return Decision.inactive(ExecutionWarning.TOKEN_NOT_CONFIGURED,
                    "backend 沒有設定 SDD 寫入權杖（BRIDGE_SDD_WRITE_TOKEN）；本批次沒有啟用 SDD 治理："
                            + "沒有預檢、沒有 FSM 同步、step_id 維持 G<g>-T<t>、事後也不會有追溯報告");
        }
        if (!ordered.stream().allMatch(SddTaskSpec::eligible)) {
            return Decision.inactive(ExecutionWarning.MIXED_SCOPE,
                    "本批次範圍內有非 SDD 來源的任務（或任務缺 stepId／specDigest）；本批次沒有啟用 SDD 治理："
                            + "沒有預檢、沒有 FSM 同步、step_id 維持 G<g>-T<t>、事後也不會有追溯報告。請把範圍限定在 SDD 來源的任務");
        }
        if (ordered.stream().map(SddTaskSpec::specDigest).distinct().count() > 1) {
            return Decision.inactive(ExecutionWarning.SPEC_MISMATCH,
                    "範圍內的 SDD 任務來自不同的規格摘要（specDigest 不一致，可能匯入過不同版本的規格）；本批次沒有啟用 SDD 治理："
                            + "沒有預檢、沒有 FSM 同步、step_id 維持 G<g>-T<t>、事後也不會有追溯報告");
        }
        Set<String> seen = new LinkedHashSet<>();
        Set<String> duplicated = new LinkedHashSet<>();
        for (SddTaskSpec spec : ordered) {
            if (!seen.add(spec.stepId())) {
                duplicated.add(spec.stepId());
            }
        }
        if (!duplicated.isEmpty()) {
            return Decision.inactive(ExecutionWarning.DUPLICATE_STEP_ID,
                    "範圍內有重複的 SDD stepId：" + String.join("、", duplicated) + "；本批次沒有啟用 SDD 治理："
                            + "沒有預檢、沒有 FSM 同步、step_id 維持 G<g>-T<t>、事後也不會有追溯報告");
        }
        Map<UUID, String> stepIds = new LinkedHashMap<>();
        Map<UUID, SddTaskSpec> active = new LinkedHashMap<>();
        for (PlannedTask planned : tasks) {
            Task task = planned.task();
            SddTaskSpec spec = specs.get(task.id());
            stepIds.put(task.id(), spec.stepId());
            active.put(task.id(), spec);
        }
        return new Decision(true, null, stepIds, active);
    }

    /**
     * 簽核人（契約 §1.10.6）：範圍內 SDD 來源任務的 {@code signedOffBy}（承襲匯入記錄的核准人；多個值時取排序最前任務的值）；全空時取觸發這次
     * 建立的人（JWT subject），所以 Backend 永遠送具名人（ADR-016 §5.2 C-1）。
     */
    public static String approverOf(List<PlannedTask> tasks, String actor) {
        for (PlannedTask planned : tasks) {
            String signedOffBy = planned.task().signedOffBy();
            if (signedOffBy != null && !signedOffBy.isBlank()) {
                return signedOffBy.strip();
            }
        }
        return actor;
    }
}
