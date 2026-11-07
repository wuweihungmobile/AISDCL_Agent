package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.research.ResearchViews.RunFact;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * 研究工作流的流程脊政策（純函式；PRD FR-R2P-01、AC-R2P-01-9；API 契約 §1.4 API-RP-04；ADR-003 D5；TCS-ResearchToPRD-P0 AT-960-4-E-2）：
 * 由「研究列的游標、Console 專案、最新內環 run、內環 FSM 視圖」算出 {@link Effective}（<b>相態不落 DB</b>）與五步 {@link Flow}。
 *
 * <p><b>不推導第二份真相</b>（D-56、D-59(3)）：步驟 1～3（{@code flow_step} 為 topic、studio、route）與 TCS 相態（{@code TCS_DRAFTING}、{@code TCS_PENDING}）
 * 一律<b>原樣取 DB 游標</b>——{@code flow_status} 由 Bridge 在寫游標的同一交易依 stage run 與 FSM 現態衍生並落庫（優先序 ESCALATED &gt; RUNNING &gt;
 * WAITING_HUMAN &gt; IDLE），本類別不再算一次；就算 {@code latestRun}、{@code fsm} 與游標互相矛盾（例：run 為 RUNNING、FSM 為 ESCALATION）也不改變結果。
 * 只有步驟 4 之後（游標在 build、deliver）且已綁定 Console 專案時，才由內環的事實衍生：FSM ESCALATION* ＝ {@code build／ESCALATED}；RELEASE_READY ＝
 * {@code deliver／RELEASE_PENDING}；RELEASE ＝ {@code deliver／DELIVERED}；最新 run RUNNING ＝ {@code BUILDING}（其中有 RETRYING 步驟＝ {@code HEALING}）；
 * PAUSED 且有待審 review_requests ＝ {@code AWAITING_HUMAN}（status WAITING_HUMAN），其餘 PAUSED ＝ {@code PAUSED}；沒有 run、FSM 在 SPEC_FROZEN 或
 * IMPLEMENTATION 且已談判 ＝ {@code BUILD_READY}。其餘情況取游標。
 *
 * <p>P0 沒有分流（P1）與內環看板（P2），游標不會走到 build 之前以外的位置——本類別先把 P1、P2 的衍生規則備齊並以表驅動測試釘住，讓日後接線只是補輸入。
 * 類別位於 {@code domain.service}，ArchUnit 判為純 Java（無 Spring、無 JPA）。
 */
public final class ResearchFlowPolicy {

    /** 工作流五步，順序固定（增減步驟＝PRD 修訂）。 */
    public static final List<String> STEP_IDS = List.of("topic", "studio", "route", "build", "deliver");

    private static final List<String> STEP_LABELS = List.of("研究", "規格工作室", "分流", "拆解與執行", "交付");
    /**
     * 五步列每一步的狀態值（閉集，契約 §1.3 {@code flow.steps[].state}）：序號小於目前步、等於目前步、目前步受阻、序號大於目前步。
     * 唯一家：DTO {@code ResearchFlow.Step} 的 Schema 描述與前端 {@code FlowStepper} 的對照表以此為準，註解一律以 {@code {@value}} 引用而不重抄字面。
     */
    public static final String STATE_DONE = "DONE";
    public static final String STATE_CURRENT = "CURRENT";
    public static final String STATE_BLOCKED = "BLOCKED";
    public static final String STATE_TODO = "TODO";
    /** 進行中的步驟遇到這三種 {@code flow_status} 時改標「受阻」（前端 {@code BLOCKING_FLOW_STATUSES} 同一判準）。 */
    private static final Set<String> BLOCKING_STATUSES = Set.of("BLOCKED", "ESCALATED", "FAILED");
    /** 游標在這三步時，{@code effective} 一律取游標。 */
    private static final Set<String> CURSOR_STEPS = Set.of("topic", "studio", "route");
    private static final Set<String> TCS_PHASES = Set.of("TCS_DRAFTING", "TCS_PENDING");

    private ResearchFlowPolicy() {
    }

    /** 研究列的游標欄位（取自 {@code research_projects}）。 */
    public record Research(String flowStep, String flowPhase, String flowStatus, String flowDetail) {
    }

    /** 研究專案已綁定的 Console 專案（P1 分流後才有；null＝尚未綁定）。 */
    public record ConsoleProject(UUID id) {
    }

    /** 內環 FSM 的視圖（P1 起接線；null＝沒有可用的視圖）：現態與是否已完成測試契約談判。 */
    public record FsmView(String currentState, boolean negotiated) {
    }

    /** 衍生後的目前位置：{@code status} 為 DB 游標的八值加衍生的 {@code PAUSED}。 */
    public record Effective(String step, String phase, String status, String detail) {
    }

    /** 五步列的一項。 */
    public record Step(String id, String label, String state, String phase, String blockedReason) {
    }

    /** 流程脊：{@code furthestStep}＝DB 游標與衍生位置中較後者（供前端判斷 {@code ?step=} 是否可達）。 */
    public record Flow(String currentStep, String furthestStep, List<Step> steps, Effective effective, String resumeHref) {
    }

    /**
     * 計算 {@code effective}（API 契約 §1.4 API-RP-04 的表）。
     *
     * @param research  研究列的游標
     * @param project   已綁定的 Console 專案；null＝未綁定，一律取游標
     * @param latestRun 該 Console 專案最新的內環 run；null＝沒有 run
     * @param fsm       內環 FSM 視圖；null＝沒有
     */
    public static Effective effective(Research research, ConsoleProject project, RunFact latestRun, FsmView fsm) {
        Effective cursor = new Effective(research.flowStep(), research.flowPhase(), research.flowStatus(),
                research.flowDetail() == null ? "" : research.flowDetail());
        if (CURSOR_STEPS.contains(research.flowStep()) || TCS_PHASES.contains(research.flowPhase()) || project == null) {
            return cursor;
        }
        String state = fsm == null || fsm.currentState() == null ? "" : fsm.currentState();
        if (state.startsWith("ESCALATION")) {
            return new Effective("build", "ESCALATED", "ESCALATED", state);
        }
        if ("RELEASE".equals(state)) {
            return new Effective("deliver", "DELIVERED", "COMPLETED", state);
        }
        if ("RELEASE_READY".equals(state)) {
            return new Effective("deliver", "RELEASE_PENDING", "WAITING_HUMAN", state);
        }
        if (latestRun != null) {
            if ("RUNNING".equals(latestRun.status())) {
                return new Effective("build", latestRun.retryingStep() ? "HEALING" : "BUILDING", "RUNNING", state);
            }
            if ("PAUSED".equals(latestRun.status())) {
                return latestRun.pendingReview() ? new Effective("build", "AWAITING_HUMAN", "WAITING_HUMAN", state)
                        : new Effective("build", "PAUSED", "PAUSED", state);
            }
            return cursor;
        }
        if (fsm != null && fsm.negotiated() && ("SPEC_FROZEN".equals(state) || "IMPLEMENTATION".equals(state))) {
            return new Effective("build", "BUILD_READY", "IDLE", state);
        }
        return cursor;
    }

    /**
     * 五步流程脊：序號小於目前步＝{@value #STATE_DONE}、等於＝{@value #STATE_CURRENT}（{@code status} 為 BLOCKED／ESCALATED／FAILED 時
     * {@value #STATE_BLOCKED}）、大於＝{@value #STATE_TODO}。
     */
    public static Flow flow(UUID researchId, Research research, ConsoleProject project, RunFact latestRun, FsmView fsm) {
        Effective effective = effective(research, project, latestRun, fsm);
        int current = Math.max(0, STEP_IDS.indexOf(effective.step()));
        int cursor = Math.max(0, STEP_IDS.indexOf(research.flowStep()));
        boolean blocked = BLOCKING_STATUSES.contains(effective.status());
        List<Step> steps = new ArrayList<>();
        for (int i = 0; i < STEP_IDS.size(); i++) {
            String state = i < current ? STATE_DONE : i > current ? STATE_TODO : blocked ? STATE_BLOCKED : STATE_CURRENT;
            boolean here = i == current;
            String reason = here && blocked ? (effective.detail().isBlank() ? effective.status() : effective.detail()) : null;
            steps.add(new Step(STEP_IDS.get(i), STEP_LABELS.get(i), state, here ? effective.phase() : null, reason));
        }
        return new Flow(STEP_IDS.get(current), STEP_IDS.get(Math.max(current, cursor)), List.copyOf(steps), effective,
                "/research/" + researchId + "?step=" + STEP_IDS.get(current));
    }
}
