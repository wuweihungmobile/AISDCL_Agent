package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.execution.ExecutionWarning;
import com.aisdlc.console.domain.model.execution.RunScope;
import com.aisdlc.console.domain.model.execution.SddTaskSpec;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.service.ExecutionPlanner.GoalWithTasks;
import com.aisdlc.console.domain.service.ExecutionPlanner.Plan;
import com.aisdlc.console.domain.service.ExecutionPlanner.Strategy;
import com.aisdlc.console.domain.service.SddBatchPolicy.Decision;
import com.aisdlc.console.support.DomainFixtures;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SDD 批次資格（契約 §1.10.5；D-115-06）。為什麼重要：資格決定「這個批次有沒有 FSM 治理」——判錯一格，要嘛 SDD 批次悄悄失去預檢與追溯報告
 * （警告該響沒響），要嘛手動專案被誤送 {@code sdd} 區塊而被 Bridge 以 422 拒絕。五項資格的<b>順序</b>也是契約的一部分（QA 依序斷言
 * {@code cause}），而且只有範圍內至少有一個 SDD 來源任務才出聲。
 */
class SddBatchPolicyTest {

    private static final String DIGEST = "sha256:" + "a".repeat(64);

    private final Project project = DomainFixtures.project("sdd-policy");
    private final Goal goal = DomainFixtures.goal(project.id(), "目標", 0);

    private Task sdd(String name, int order, String stepId, String digest, String signedOffBy) {
        return DomainFixtures.sddTask(goal.id(), name, order, DomainFixtures.sddSpec(stepId, digest), signedOffBy);
    }

    private Plan planOf(Task... tasks) {
        List<GoalWithTasks> goals = List.of(new GoalWithTasks(goal, List.of(tasks)));
        return ExecutionPlanner.plan(goals, Map.of(goal.id(), Set.of()), RunScope.all(), Strategy.TOPOLOGICAL, true);
    }

    private static Map<UUID, SddTaskSpec> specsOf(Plan plan) {
        Map<UUID, SddTaskSpec> specs = new LinkedHashMap<>();
        plan.tasks().forEach(p -> specs.put(p.task().id(), parse(p.task().passCriteriaSpec())));
        return specs;
    }

    /** 測試用的最小解析（正式的解析在 persistence 介面卡，這裡只認 DomainFixtures.sddSpec 的形狀）。 */
    private static SddTaskSpec parse(String json) {
        if (json == null || !json.contains("\"source\":\"sdd\"")) {
            return SddTaskSpec.NONE;
        }
        return new SddTaskSpec("sdd", field(json, "stepId"), field(json, "specDigest"), false, null);
    }

    private static String field(String json, String name) {
        int at = json.indexOf("\"" + name + "\":\"");
        if (at < 0) {
            return null;
        }
        int start = at + name.length() + 4;
        String value = json.substring(start, json.indexOf('"', start));
        return value.isEmpty() ? null : value;
    }

    private Decision decide(boolean bound, boolean token, Task... tasks) {
        Plan plan = planOf(tasks);
        return SddBatchPolicy.decide(bound, token, plan.tasks(), specsOf(plan));
    }

    private static void assertInactive(Decision decision, String cause) {
        assertThat(decision.active()).isFalse();
        assertThat(decision.warning()).isNotNull();
        assertThat(decision.warning().code()).isEqualTo("sdd_governance_inactive");
        assertThat(decision.warning().cause()).isEqualTo(cause);
        assertThat(decision.warning().detail()).as("給人看的中文說明").isNotBlank().contains("沒有啟用 SDD 治理");
        assertThat(decision.stepIds()).isEmpty();
        assertThat(decision.specs()).isEmpty();
    }

    @Test
    void aBatchWithoutAnySddTaskIsSilentlyInactiveWhateverElseIsMissing() {
        Task manual = DomainFixtures.task(goal.id(), "手動", 0);

        for (boolean bound : List.of(true, false)) {
            for (boolean token : List.of(true, false)) {
                Decision decision = decide(bound, token, manual);
                assertThat(decision).as("bound=" + bound + " token=" + token).isSameAs(Decision.NONE);
                assertThat(decision.warning()).as("沒有 SDD 來源任務就不出聲").isNull();
            }
        }
    }

    @Test
    void anEligibleBatchIsActiveAndCarriesTheStepIdsAndTheSpecs() {
        Task a = sdd("A", 0, "sdd-greenfield-at-001-1-1", DIGEST, null);
        Task b = sdd("B", 1, "sdd-greenfield-at-001-1-2", DIGEST, null);

        Decision decision = decide(true, true, a, b);

        assertThat(decision.active()).isTrue();
        assertThat(decision.warning()).isNull();
        assertThat(decision.stepIds()).containsEntry(a.id(), "sdd-greenfield-at-001-1-1")
                .containsEntry(b.id(), "sdd-greenfield-at-001-1-2");
        assertThat(decision.specs().get(a.id()).specDigest()).isEqualTo(DIGEST);
    }

    @Test
    void anUnboundProjectIsNotBound() {
        assertInactive(decide(false, true, sdd("A", 0, "sdd-x-at-001-1-1", DIGEST, null)), ExecutionWarning.NOT_BOUND);
    }

    @Test
    void aMissingWriteTokenIsTokenNotConfigured() {
        assertInactive(decide(true, false, sdd("A", 0, "sdd-x-at-001-1-1", DIGEST, null)),
                ExecutionWarning.TOKEN_NOT_CONFIGURED);
    }

    @Test
    void aManualTaskNextToASddTaskIsMixedScope() {
        assertInactive(decide(true, true, sdd("A", 0, "sdd-x-at-001-1-1", DIGEST, null),
                DomainFixtures.task(goal.id(), "手動", 1)), ExecutionWarning.MIXED_SCOPE);
    }

    @Test
    void aSddTaskWithoutAStepIdOrADigestIsAlsoMixedScope() {
        assertInactive(decide(true, true, DomainFixtures.sddTask(goal.id(), "A", 0,
                "{\"source\":\"sdd\",\"specDigest\":\"" + DIGEST + "\"}", null)), ExecutionWarning.MIXED_SCOPE);
        assertInactive(decide(true, true, DomainFixtures.sddTask(goal.id(), "B", 0,
                "{\"source\":\"sdd\",\"stepId\":\"sdd-x-at-001-1-1\"}", null)), ExecutionWarning.MIXED_SCOPE);
        assertInactive(decide(true, true, DomainFixtures.sddTask(goal.id(), "C", 0,
                "{\"source\":\"sdd\",\"stepId\":\"\",\"specDigest\":\"" + DIGEST + "\"}", null)),
                ExecutionWarning.MIXED_SCOPE);
    }

    @Test
    void aTaskOfAnotherSourceAloneIsNotASddBatchAtAll() {
        Decision decision = decide(true, true, DomainFixtures.sddTask(goal.id(), "D", 0, "{\"source\":\"decompose\"}", null));

        assertThat(decision).as("source 不是 sdd：沒有 SDD 來源任務，不出聲").isSameAs(Decision.NONE);
    }

    @Test
    void tasksFromDifferentSpecDigestsAreSpecMismatch() {
        assertInactive(decide(true, true, sdd("A", 0, "sdd-x-at-001-1-1", DIGEST, null),
                sdd("B", 1, "sdd-x-at-001-1-2", "sha256:" + "b".repeat(64), null)), ExecutionWarning.SPEC_MISMATCH);
    }

    @Test
    void repeatedStepIdsAreDuplicateStepIdAndTheDetailNamesThem() {
        Decision decision = decide(true, true, sdd("A", 0, "sdd-x-at-001-1-1", DIGEST, null),
                sdd("B", 1, "sdd-x-at-001-1-1", DIGEST, null));

        assertInactive(decision, ExecutionWarning.DUPLICATE_STEP_ID);
        assertThat(decision.warning().detail()).contains("sdd-x-at-001-1-1");
    }

    @Test
    void theCausesAreCheckedInTheContractsOrder() {
        Task mismatchAndDuplicate = sdd("A", 0, "sdd-x-at-001-1-1", DIGEST, null);
        Task other = sdd("B", 1, "sdd-x-at-001-1-1", "sha256:" + "b".repeat(64), null);
        Task manual = DomainFixtures.task(goal.id(), "手動", 2);

        assertInactive(decide(false, false, mismatchAndDuplicate, other, manual), ExecutionWarning.NOT_BOUND);
        assertInactive(decide(true, false, mismatchAndDuplicate, other, manual), ExecutionWarning.TOKEN_NOT_CONFIGURED);
        assertInactive(decide(true, true, mismatchAndDuplicate, other, manual), ExecutionWarning.MIXED_SCOPE);
        assertInactive(decide(true, true, mismatchAndDuplicate, other), ExecutionWarning.SPEC_MISMATCH);
    }

    @Test
    void theApproverIsTheFirstNonBlankSignedOffByInPlanOrderElseTheActor() {
        Plan inherited = planOf(sdd("A", 0, "sdd-x-at-001-1-1", DIGEST, "  "), sdd("B", 1, "sdd-x-at-001-1-2", DIGEST, " 張三 "),
                sdd("C", 2, "sdd-x-at-001-1-3", DIGEST, "李四"));
        Plan anonymous = planOf(sdd("A", 0, "sdd-x-at-001-1-1", DIGEST, null));

        assertThat(SddBatchPolicy.approverOf(inherited.tasks(), "operator")).as("排序最前的非空值，去前後空白").isEqualTo("張三");
        assertThat(SddBatchPolicy.approverOf(anonymous.tasks(), "operator")).as("全空取觸發的人，永遠具名").isEqualTo("operator");
    }
}
