package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.AlertEventData;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Frame;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Kind;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.LogEventData;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.MetricUpdateEventData;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.ProgressUpdateEventData;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.StatusChangeEventData;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.TokenUpdateEventData;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeEvent;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Node;
import com.aisdlc.console.domain.model.execution.DagSnapshot.NodeKind;
import com.aisdlc.console.domain.model.execution.RunStatus;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 前端 SSE 框架的組裝（契約 §2.5～§2.7；純函式）。為什麼重要：即時事件與 {@code Last-Event-ID} 重播共用這些函式，
 * 兩條路徑必須產生同樣形狀的框架，否則重連之後客戶端看到的訊息會與即時看到的不同；STEP 訊息樣板是契約逐字規定的，
 * 前端與 E2E 腳本直接比對文字。
 */
class StreamFramesTest {

    private static final String TS = "2026-10-15T08:00:00Z";

    private static BridgeEvent event(int seq, String name, Object... keyValues) {
        Map<String, Object> data = new HashMap<>();
        for (int i = 0; i < keyValues.length; i += 2) {
            data.put((String) keyValues[i], keyValues[i + 1]);
        }
        return new BridgeEvent(seq, TS, name, data);
    }

    private static Node task() {
        return new Node(UUID.fromString("33333333-3333-3333-3333-333333333333"), NodeKind.TASK, "初始化",
                UUID.fromString("44444444-4444-4444-4444-444444444444"), "G1-T1", 1);
    }

    // ── /logs ──────────────────────────────────────────────────────────────────

    @Test
    void aStatusChangeCarriesBothTheFoldedAndTheOriginalStatusWithAnEmptyReasonWhenMissing() {
        Frame pausing = StreamFrames.statusChange(event(12, "status"), BridgeStatus.PAUSING, null);
        Frame cancelled = StreamFrames.statusChange(event(13, "status"), BridgeStatus.CANCELLED, "使用者取消");

        assertThat(pausing.kind()).isEqualTo(Kind.LOGS);
        assertThat(pausing.id()).isEqualTo("12");
        assertThat(pausing.event()).isEqualTo("status-change");
        StatusChangeEventData data = (StatusChangeEventData) pausing.data();
        assertThat(data.runStatus()).as("PAUSING 對前端折成 RUNNING").isEqualTo(RunStatus.RUNNING);
        assertThat(data.bridgeStatus()).isEqualTo(BridgeStatus.PAUSING);
        assertThat(data.reason()).isEmpty();
        assertThat(((StatusChangeEventData) cancelled.data()).reason()).isEqualTo("使用者取消");
    }

    @Test
    void anEngineLogLineNormalisesItsLevelAndIsTaggedWithTheCurrentStepWhenKnown() {
        Frame warning = StreamFrames.engineLog(event(5, "log", "level", "warning", "line", "slow"), task(), "G1-T1");
        Frame bare = StreamFrames.engineLog(event(6, "log"), null, null);
        Frame error = StreamFrames.engineLog(event(7, "log", "level", "Error", "line", "boom"), null, null);

        LogEventData tagged = (LogEventData) warning.data();
        assertThat(tagged.source()).isEqualTo("ENGINE");
        assertThat(tagged.level()).as("WARNING 一律寫成 WARN").isEqualTo("WARN");
        assertThat(tagged.message()).isEqualTo("slow");
        assertThat(tagged.stepId()).isEqualTo("G1-T1");
        assertThat(tagged.taskId()).isEqualTo(task().id());
        assertThat(tagged.goalId()).isEqualTo(task().goalId());
        LogEventData none = (LogEventData) bare.data();
        assertThat(none.level()).as("沒帶 level 當 INFO").isEqualTo("INFO");
        assertThat(none.message()).isEmpty();
        assertThat(none.stepId()).isNull();
        assertThat(none.taskId()).isNull();
        assertThat(((LogEventData) error.data()).level()).isEqualTo("ERROR");
    }

    @Test
    void aStepLogUsesTheContractMessageTemplatesAndOnlyCompletedRowsCarryTokens() {
        Node node = task();
        LogEventData started = (LogEventData) StreamFrames.stepLog(event(1, "step"), node, "G1-T1", "STARTED", 1, 1, null,
                null).data();
        LogEventData retrying = (LogEventData) StreamFrames.stepLog(event(2, "step"), node, "G1-T1", "RETRYING", 1, 2, null,
                null).data();
        LogEventData completed = (LogEventData) StreamFrames.stepLog(event(3, "step"), node, "G1-T1", "COMPLETED", 1, 1,
                1240L, null).data();
        LogEventData failed = (LogEventData) StreamFrames.stepLog(event(4, "step"), node, "G1-T1", "FAILED", 1, 2, 2480L,
                "重試 1 次仍失敗").data();

        assertThat(started.message()).isEqualTo("開始：初始化（G1-T1，第 1 次）");
        assertThat(retrying.message()).isEqualTo("重試：初始化（G1-T1，第 2 次）");
        assertThat(completed.message()).isEqualTo("完成：初始化（G1-T1） Token: 1240");
        assertThat(failed.message()).isEqualTo("失敗：初始化（G1-T1，第 2 次）：重試 1 次仍失敗");
        assertThat(started.level()).isEqualTo("INFO");
        assertThat(retrying.level()).isEqualTo("WARN");
        assertThat(failed.level()).isEqualTo("ERROR");
        assertThat(started.source()).isEqualTo("STEP");
        assertThat(started.tokensUsed()).isNull();
        assertThat(completed.tokensUsed()).isEqualTo(1240L);
        assertThat(failed.tokensUsed()).as("FAILED 列不帶 tokensUsed 欄位（只在訊息裡看不到）").isNull();
        assertThat(completed.stepNumber()).isEqualTo(1);
        assertThat(completed.attempt()).isEqualTo(1);
        assertThat(completed.taskName()).isEqualTo("初始化");
    }

    @Test
    void stepMessageDegradesGracefullyForMissingTokensErrorsAndUnknownStatuses() {
        assertThat(StreamFrames.stepMessage("COMPLETED", "T", "S1", 1, null, null)).isEqualTo("完成：T（S1）");
        assertThat(StreamFrames.stepMessage("COMPLETED", "T", "S1", 1, 0L, null)).as("0 個 Token 不顯示").isEqualTo("完成：T（S1）");
        assertThat(StreamFrames.stepMessage("FAILED", "T", "S1", 3, null, null)).isEqualTo("失敗：T（S1，第 3 次）");
        assertThat(StreamFrames.stepMessage("FAILED", "T", "S1", 3, null, "  ")).isEqualTo("失敗：T（S1，第 3 次）");
        assertThat(StreamFrames.stepMessage("SKIPPED", "T", "S1", 1, null, null)).isEqualTo("SKIPPED：T（S1）");
        assertThat(StreamFrames.stepLevel(null)).isEqualTo("INFO");
        assertThat(StreamFrames.stepLevel("COMPLETED")).isEqualTo("INFO");
    }

    @Test
    void aStepLogOfAnUnknownTaskFallsBackToTheStepIdAsItsName() {
        LogEventData data = (LogEventData) StreamFrames.stepLog(event(9, "step"), null, "G9-T9", "STARTED", 4, 1, null,
                null).data();

        assertThat(data.message()).isEqualTo("開始：G9-T9（G9-T9，第 1 次）");
        assertThat(data.taskId()).isNull();
        assertThat(data.taskName()).isEqualTo("G9-T9");
        assertThat(data.goalId()).isNull();
    }

    @Test
    void anEngineAlertIsForwardedWithTheSeverityOfItsLevelAndTheBridgeSeqAsItsId() {
        Frame error = StreamFrames.engineAlert(event(20, "alert", "level", "error", "code", "ESCALATION",
                "message", "升級", "step_id", "G1-T1"), null, null);
        Frame warning = StreamFrames.engineAlert(event(21, "alert", "level", "WARNING", "code", "X"), null, "run");
        Frame info = StreamFrames.engineAlert(event(22, "alert", "code", "RESTORE", "message", "已還原"), null, null);

        AlertEventData data = (AlertEventData) error.data();
        assertThat(error.id()).isEqualTo("20");
        assertThat(data.origin()).isEqualTo("ENGINE");
        assertThat(data.severity()).isEqualTo("CRITICAL");
        assertThat(data.code()).isEqualTo("ESCALATION");
        assertThat(data.stepId()).isEqualTo("G1-T1");
        assertThat(data.alertId()).as("沒有持久化鏡像就沒有 alertId").isNull();
        assertThat(((AlertEventData) warning.data()).severity()).isEqualTo("WARNING");
        assertThat(((AlertEventData) warning.data()).subject()).isEqualTo("run");
        assertThat(((AlertEventData) info.data()).severity()).isEqualTo("INFO");
    }

    @Test
    void aConnectionAlertHasNoIdSoItIsNeverDeduplicatedOrReplayed() {
        Frame frame = StreamFrames.connectionAlert(31, "BRIDGE_UNREACHABLE", "暫時無法連線", Instant.parse(TS));

        assertThat(frame.hasId()).isFalse();
        assertThat(frame.id()).isNull();
        AlertEventData data = (AlertEventData) frame.data();
        assertThat(data.origin()).isEqualTo("CONSOLE");
        assertThat(data.code()).isEqualTo("BRIDGE_UNREACHABLE");
        assertThat(data.severity()).isEqualTo("WARNING");
        assertThat(data.seq()).as("錨點只是告訴前端它發生在哪則事件之後").isEqualTo(31);
        assertThat(data.ts()).isEqualTo(TS);
    }

    // ── /metrics ───────────────────────────────────────────────────────────────

    @Test
    void progressRoundsToOneDecimalAndAnEmptyPlanIsZeroPercent() {
        ProgressUpdateEventData two = (ProgressUpdateEventData) StreamFrames.progress(40, 1, TS, BridgeStatus.RUNNING, 2,
                3, null).data();
        ProgressUpdateEventData none = (ProgressUpdateEventData) StreamFrames.progress(40, 1, TS, BridgeStatus.PAUSING, 0,
                0, null).data();

        assertThat(two.progressPct()).isEqualTo(66.7);
        assertThat(none.progressPct()).isEqualTo(0.0);
        assertThat(none.runStatus()).isEqualTo(RunStatus.RUNNING);
        assertThat(none.bridgeStatus()).isEqualTo(BridgeStatus.PAUSING);
        Frame frame = StreamFrames.progress(40, 1, TS, BridgeStatus.RUNNING, 1, 3, null);
        assertThat(frame.kind()).isEqualTo(Kind.METRICS);
        assertThat(frame.id()).isEqualTo("40.1");
        assertThat(frame.event()).isEqualTo("progress-update");
    }

    @Test
    void tokenAndMetricFramesShowBudgetUsageOnlyWhenThereIsABudget() {
        UUID taskId = UUID.randomUUID();
        TokenUpdateEventData withBudget = (TokenUpdateEventData) StreamFrames.token(40, 2, TS, 3720, 1240, 0.6, 100000L,
                taskId).data();
        TokenUpdateEventData noBudget = (TokenUpdateEventData) StreamFrames.token(40, 2, TS, 3720, 1240, 0.0, null,
                null).data();
        TokenUpdateEventData zeroBudget = (TokenUpdateEventData) StreamFrames.token(40, 2, TS, 3720, 1240, 0.0, 0L,
                null).data();
        MetricUpdateEventData metric = (MetricUpdateEventData) StreamFrames.metric(40, 3, TS, 2, 1, 3, 1, 1.0 / 3, 3720,
                100000L, 95).data();
        MetricUpdateEventData noBudgetMetric = (MetricUpdateEventData) StreamFrames.metric(40, 3, TS, 0, 0, 3, 0, 0.0, 0,
                null, 0).data();

        assertThat(withBudget.budgetUsageRate()).isEqualTo(3.7);
        assertThat(withBudget.taskId()).isEqualTo(taskId);
        assertThat(noBudget.budgetUsageRate()).isNull();
        assertThat(zeroBudget.budgetUsageRate()).as("預算 0 視為沒有預算，不除以零").isNull();
        assertThat(metric.tokenBudgetUsageRate()).isEqualTo(3.7);
        assertThat(metric.averageRetryCount()).as("原樣帶入（四捨五入在呼叫端）").isEqualTo(1.0 / 3);
        assertThat(metric.elapsedSec()).isEqualTo(95);
        assertThat(noBudgetMetric.tokenBudgetUsageRate()).isNull();
    }

    @Test
    void roundingIsHalfUpOnTheDecimalExpansionNotOnTheBinaryDouble() {
        assertThat(StreamFrames.round1(0.25)).isEqualTo(0.3);
        assertThat(StreamFrames.round1(66.65)).isEqualTo(66.7);
        assertThat(StreamFrames.round2(1.005)).isEqualTo(1.01);
        assertThat(StreamFrames.round2(0.3333333)).isEqualTo(0.33);
        assertThat(StreamFrames.round1(100.0)).isEqualTo(100.0);
    }
}
