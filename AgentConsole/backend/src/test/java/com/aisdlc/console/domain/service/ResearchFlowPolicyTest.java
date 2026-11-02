package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.research.ResearchViews.RunFact;
import com.aisdlc.console.domain.service.ResearchFlowPolicy.ConsoleProject;
import com.aisdlc.console.domain.service.ResearchFlowPolicy.Effective;
import com.aisdlc.console.domain.service.ResearchFlowPolicy.Flow;
import com.aisdlc.console.domain.service.ResearchFlowPolicy.FsmView;
import com.aisdlc.console.domain.service.ResearchFlowPolicy.Research;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;
import static org.assertj.core.api.Assertions.assertThat;

/**
 * 流程脊政策的表驅動測試（TCS-ResearchToPRD-P0 AT-960-4-E-2；PRD AC-R2P-01-9）。為什麼重要：{@code flow_status} 由 Bridge 在寫游標的同一交易依 stage run 與 FSM 現態衍生並落庫，
 * 政策若對步驟 1～3 另行推導，就有了「第二份真相」——前端看到的相態會隨 latestRun 與 FSM 視圖的讀取時機翻動（D-56）；而步驟 4 之後（內環）的相態不落庫，只能由事實衍生，
 * 衍生規則寫錯＝「執行中」被顯示成「待人工」，使用者在錯的時機被打擾。
 */
class ResearchFlowPolicyTest {

    private static final UUID ID = UUID.fromString("00000000-0000-4000-8000-000000000001");
    private static final ConsoleProject BOUND = new ConsoleProject(UUID.fromString("00000000-0000-4000-8000-0000000000c1"));

    /** 一列輸入與期望的 effective（step／phase／status）。 */
    private record Row(String label, Research research, ConsoleProject project, RunFact run, FsmView fsm, String step, String phase, String status) {
    }

    private static Research cursor(String step, String phase, String status) {
        return new Research(step, phase, status, "");
    }

    private static List<Row> rows() {
        FsmView escalated = new FsmView("ESCALATION", true);
        List<Row> rows = new ArrayList<>();
        // 游標在 topic、studio、route：相態與狀態原樣取 DB 游標（四列，TCS 逐字）
        rows.add(new Row("topic／EVIDENCE_READY／IDLE", cursor("topic", "EVIDENCE_READY", "IDLE"), null, null, null, "topic", "EVIDENCE_READY", "IDLE"));
        rows.add(new Row("studio／REVIEWING／RUNNING", cursor("studio", "REVIEWING", "RUNNING"), null, null, null, "studio", "REVIEWING", "RUNNING"));
        rows.add(new Row("studio／GATE0_PENDING／WAITING_HUMAN", cursor("studio", "GATE0_PENDING", "WAITING_HUMAN"), null, null, null, "studio",
                "GATE0_PENDING", "WAITING_HUMAN"));
        rows.add(new Row("studio／REVIEWING／ESCALATED", cursor("studio", "REVIEWING", "ESCALATED"), null, null, null, "studio", "REVIEWING", "ESCALATED"));
        // 輸入互相矛盾（latestRun RUNNING、FSM ESCALATION、已綁定專案）也不改變結果：政策不得另行推導第二份真相
        rows.add(new Row("矛盾輸入不改變游標（步驟 2）", cursor("studio", "REVIEWING", "RUNNING"), BOUND, new RunFact("RUNNING", true, false), escalated, "studio",
                "REVIEWING", "RUNNING"));
        rows.add(new Row("矛盾輸入不改變游標（步驟 3）", cursor("route", "ROUTING", "IDLE"), BOUND, new RunFact("PAUSED", false, true), escalated, "route",
                "ROUTING", "IDLE"));
        // TCS 相態：原樣取游標，即使游標步驟在 build、且 FSM 在 ESCALATION
        rows.add(new Row("TCS_DRAFTING 取游標", cursor("build", "TCS_DRAFTING", "RUNNING"), BOUND, null, escalated, "build", "TCS_DRAFTING", "RUNNING"));
        rows.add(new Row("TCS_PENDING 取游標", cursor("build", "TCS_PENDING", "WAITING_HUMAN"), BOUND, new RunFact("RUNNING", false, false), escalated,
                "build", "TCS_PENDING", "WAITING_HUMAN"));
        // 步驟 4 之後且已綁定：由內環事實衍生
        rows.add(new Row("無 run、SPEC_FROZEN 且已談判＝BUILD_READY", cursor("build", "ROUTED", "IDLE"), BOUND, null, new FsmView("SPEC_FROZEN", true), "build",
                "BUILD_READY", "IDLE"));
        rows.add(new Row("無 run、IMPLEMENTATION 且已談判＝BUILD_READY", cursor("build", "ROUTED", "IDLE"), BOUND, null, new FsmView("IMPLEMENTATION", true),
                "build", "BUILD_READY", "IDLE"));
        rows.add(new Row("SPEC_FROZEN 未談判＝取游標", cursor("build", "ROUTED", "IDLE"), BOUND, null, new FsmView("SPEC_FROZEN", false), "build", "ROUTED", "IDLE"));
        rows.add(new Row("最新 run RUNNING＝BUILDING", cursor("build", "ROUTED", "IDLE"), BOUND, new RunFact("RUNNING", false, false), new FsmView("IMPLEMENTATION", true),
                "build", "BUILDING", "RUNNING"));
        rows.add(new Row("RUNNING 且有 RETRYING 步驟＝HEALING", cursor("build", "ROUTED", "IDLE"), BOUND, new RunFact("RUNNING", true, false),
                new FsmView("IMPLEMENTATION", true), "build", "HEALING", "RUNNING"));
        rows.add(new Row("PAUSED 且有待審 review_requests＝AWAITING_HUMAN", cursor("build", "ROUTED", "IDLE"), BOUND, new RunFact("PAUSED", false, true),
                new FsmView("IMPLEMENTATION", true), "build", "AWAITING_HUMAN", "WAITING_HUMAN"));
        rows.add(new Row("PAUSED 其餘＝PAUSED", cursor("build", "ROUTED", "IDLE"), BOUND, new RunFact("PAUSED", false, false), new FsmView("IMPLEMENTATION", true),
                "build", "PAUSED", "PAUSED"));
        rows.add(new Row("最新 run 已終態＝取游標", cursor("build", "ROUTED", "IDLE"), BOUND, new RunFact("COMPLETED", false, false), new FsmView("IMPLEMENTATION", true),
                "build", "ROUTED", "IDLE"));
        rows.add(new Row("FSM ESCALATION＝ESCALATED", cursor("build", "ROUTED", "IDLE"), BOUND, new RunFact("RUNNING", false, false), escalated, "build",
                "ESCALATED", "ESCALATED"));
        rows.add(new Row("FSM ESCALATION_FINAL＝ESCALATED", cursor("build", "ROUTED", "IDLE"), BOUND, null, new FsmView("ESCALATION_FINAL", false), "build",
                "ESCALATED", "ESCALATED"));
        rows.add(new Row("RELEASE_READY＝deliver／RELEASE_PENDING", cursor("build", "ROUTED", "IDLE"), BOUND, null, new FsmView("RELEASE_READY", true), "deliver",
                "RELEASE_PENDING", "WAITING_HUMAN"));
        rows.add(new Row("RELEASE＝deliver／DELIVERED", cursor("build", "ROUTED", "IDLE"), BOUND, null, new FsmView("RELEASE", true), "deliver", "DELIVERED",
                "COMPLETED"));
        rows.add(new Row("未綁定 Console 專案＝取游標", cursor("build", "ROUTED", "IDLE"), null, new RunFact("RUNNING", false, false), escalated, "build", "ROUTED",
                "IDLE"));
        rows.add(new Row("沒有 FSM 視圖也沒有 run＝取游標", cursor("deliver", "ROUTED", "IDLE"), BOUND, null, null, "deliver", "ROUTED", "IDLE"));
        return rows;
    }

    @Test
    void AT_960_4_E_2_effectiveIsTableDrivenAndNeverDerivesASecondTruthForTheCursorSteps() {
        for (Row row : rows()) {
            Effective effective = ResearchFlowPolicy.effective(row.research(), row.project(), row.run(), row.fsm());
            assertThat(effective.step()).as("%s：step", row.label()).isEqualTo(row.step());
            assertThat(effective.phase()).as("%s：phase", row.label()).isEqualTo(row.phase());
            assertThat(effective.status()).as("%s：status", row.label()).isEqualTo(row.status());
        }
    }

    @Test
    void AT_960_4_E_2_aNullDetailBecomesAnEmptyStringAndTheCursorDetailIsKeptVerbatim() {
        assertThat(ResearchFlowPolicy.effective(new Research("topic", "INGESTED", "FAILED", null), null, null, null).detail()).isEmpty();
        assertThat(ResearchFlowPolicy.effective(new Research("topic", "INGESTED", "FAILED", "init_failed:fsm"), null, null, null).detail())
                .isEqualTo("init_failed:fsm");
    }

    @Test
    void AT_960_4_E_2_theFlowHasExactlyFiveStepsAndMarksDoneCurrentTodoBeforeAndAfterTheCurrentStep() {
        Flow flow = ResearchFlowPolicy.flow(ID, cursor("studio", "REVIEWING", "RUNNING"), null, null, null);

        assertThat(flow.steps()).extracting(ResearchFlowPolicy.Step::id).containsExactly("topic", "studio", "route", "build", "deliver");
        assertThat(flow.steps()).extracting(ResearchFlowPolicy.Step::state).containsExactly("DONE", "CURRENT", "TODO", "TODO", "TODO");
        assertThat(flow.currentStep()).isEqualTo("studio");
        assertThat(flow.furthestStep()).isEqualTo("studio");
        assertThat(flow.resumeHref()).isEqualTo("/research/" + ID + "?step=studio");
        assertThat(flow.steps().get(1).phase()).isEqualTo("REVIEWING");
        assertThat(flow.steps().get(0).phase()).as("只有目前步帶相態").isNull();
        assertThat(flow.effective().status()).isEqualTo("RUNNING");
    }

    @Test
    void AT_960_4_E_2_aBlockingStatusMarksTheCurrentStepBlockedWithTheDetailAsTheReason() {
        for (String status : List.of("BLOCKED", "ESCALATED", "FAILED")) {
            Flow flow = ResearchFlowPolicy.flow(ID, new Research("topic", "INGESTED", status, "init_failed:fsm"), null, null, null);
            assertThat(flow.steps().get(0).state()).as(status).isEqualTo("BLOCKED");
            assertThat(flow.steps().get(0).blockedReason()).as(status).isEqualTo("init_failed:fsm");
            assertThat(flow.steps().get(1).state()).as(status).isEqualTo("TODO");
        }
        Flow noDetail = ResearchFlowPolicy.flow(ID, new Research("studio", "REVIEWING", "ESCALATED", ""), null, null, null);
        assertThat(noDetail.steps().get(1).blockedReason()).as("沒有說明時以狀態當原因").isEqualTo("ESCALATED");
    }

    @Test
    void AT_960_4_E_2_theFurthestStepIsTheLaterOfTheCursorAndTheDerivedPosition() {
        // 游標停在 route，但步驟 4 的衍生位置已在 deliver：furthest＝deliver 或游標中較後者；current 取衍生位置
        Flow derived = ResearchFlowPolicy.flow(ID, cursor("build", "ROUTED", "IDLE"), BOUND, null, new FsmView("RELEASE", true));
        assertThat(derived.currentStep()).isEqualTo("deliver");
        assertThat(derived.furthestStep()).isEqualTo("deliver");
        assertThat(derived.steps()).extracting(ResearchFlowPolicy.Step::state).containsExactly("DONE", "DONE", "DONE", "DONE", "CURRENT");
        assertThat(derived.resumeHref()).endsWith("?step=deliver");

        // 衍生位置比游標前面（例：游標在 deliver、FSM 視圖暫時讀到 ESCALATION 後又恢復）：furthest 仍取較後者
        Flow behind = ResearchFlowPolicy.flow(ID, cursor("deliver", "ROUTED", "IDLE"), BOUND, null, escalatedFsm());
        assertThat(behind.currentStep()).isEqualTo("build");
        assertThat(behind.furthestStep()).isEqualTo("deliver");
    }

    private static FsmView escalatedFsm() {
        return new FsmView("ESCALATION", true);
    }

    @Test
    void AT_960_4_E_2_thePolicyClassLivesInDomainServiceAndIsPlainJava() {
        assertThat(ResearchFlowPolicy.class.getPackageName()).isEqualTo("com.aisdlc.console.domain.service");
        noClasses().that().haveSimpleNameStartingWith("ResearchFlowPolicy")
                .should().dependOnClassesThat().resideInAnyPackage("org.springframework..", "jakarta..", "org.hibernate..", "tools.jackson..", "com.fasterxml..",
                        "io.swagger..", "..application..", "..adapter..", "..infrastructure..")
                .check(new ClassFileImporter().withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS).importPackages("com.aisdlc.console.domain"));
    }
}
