package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.CurrentStepView;
import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.ReviewView;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.AlertEventData;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Frame;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Kind;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.LogEventData;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.MetricUpdateEventData;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.ProgressUpdateEventData;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.ReviewRequestEventData;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.StatusChangeEventData;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.TokenUpdateEventData;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeEvent;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.DagSnapshot;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Node;
import com.aisdlc.console.domain.model.execution.ReviewRequest;
import com.aisdlc.console.domain.model.monitor.Alert;
import com.aisdlc.console.domain.service.ReviewGatePolicy;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.Locale;

/**
 * 前端 SSE 框架的組裝（契約 §2.5～§2.7）。即時事件（{@code RunEventProcessor}）與 {@code Last-Event-ID} 重播
 * （{@code StreamService}）共用，所以兩條路徑產生的框架完全同形。純函式，不碰資料庫。
 */
final class StreamFrames {

    private StreamFrames() {
    }

    // ── /logs ──────────────────────────────────────────────────────────────────

    static Frame statusChange(BridgeEvent e, BridgeStatus status, String reason) {
        return new Frame(Kind.LOGS, e.seq(), 0, "status-change",
                new StatusChangeEventData(e.seq(), e.ts(), status.fold(), status, reason == null ? "" : reason));
    }

    /** 引擎 stdout 的一行（Bridge {@code log} 事件）；消費者已知目前步驟時帶 {@code stepId}／{@code taskId}。 */
    static Frame engineLog(BridgeEvent e, Node currentStep, String currentStepId) {
        String level = e.text("level") == null ? "INFO" : e.text("level").toUpperCase(Locale.ROOT);
        if ("WARNING".equals(level)) {
            level = "WARN";
        }
        String line = e.text("line") == null ? "" : e.text("line");
        return new Frame(Kind.LOGS, e.seq(), 0, "log", new LogEventData(e.seq(), e.ts(), "ENGINE", level, line,
                currentStepId, null, currentStep == null ? null : currentStep.id(), null,
                currentStep == null ? null : currentStep.goalId(), null, null, null));
    }

    /** 由 step 事件衍生的摘要行（{@code source=STEP}）。 */
    static Frame stepLog(BridgeEvent e, Node node, String stepId, String stepStatus, int position, int attempt,
                         Long tokens, String error) {
        String name = node == null ? stepId : node.label();
        return new Frame(Kind.LOGS, e.seq(), 0, "log", new LogEventData(e.seq(), e.ts(), "STEP",
                stepLevel(stepStatus), stepMessage(stepStatus, name, stepId, attempt, tokens, error), stepId, position,
                node == null ? null : node.id(), name, node == null ? null : node.goalId(), attempt, stepStatus,
                "COMPLETED".equals(stepStatus) ? tokens : null));
    }

    static String stepLevel(String stepStatus) {
        return switch (stepStatus == null ? "" : stepStatus) {
            case "RETRYING" -> "WARN";
            case "FAILED" -> "ERROR";
            default -> "INFO";
        };
    }

    /** 契約 §2.5 的 STEP 訊息樣板（逐字）。 */
    static String stepMessage(String stepStatus, String taskName, String stepId, int attempt, Long tokens,
                              String error) {
        return switch (stepStatus == null ? "" : stepStatus) {
            case "STARTED" -> "開始：" + taskName + "（" + stepId + "，第 " + attempt + " 次）";
            case "RETRYING" -> "重試：" + taskName + "（" + stepId + "，第 " + attempt + " 次）";
            case "COMPLETED" -> "完成：" + taskName + "（" + stepId + "）"
                    + (tokens != null && tokens > 0 ? " Token: " + tokens : "");
            case "FAILED" -> "失敗：" + taskName + "（" + stepId + "，第 " + attempt + " 次）"
                    + (error == null || error.isBlank() ? "" : "：" + error);
            default -> stepStatus + "：" + taskName + "（" + stepId + "）";
        };
    }

    /** Bridge {@code alert} 事件原樣轉發（{@code origin=ENGINE}，id＝seq）。 */
    static Frame engineAlert(BridgeEvent e, Alert persisted, String subject) {
        String level = e.text("level") == null ? "info" : e.text("level").toLowerCase(Locale.ROOT);
        String severity = switch (level) {
            case "error" -> "CRITICAL";
            case "warning" -> "WARNING";
            default -> "INFO";
        };
        return new Frame(Kind.LOGS, e.seq(), 0, "alert", new AlertEventData(e.seq(), null, e.ts(), "ENGINE",
                persisted == null ? null : persisted.id(), persisted == null ? null : persisted.rule().name(),
                e.text("code"), severity, subject, e.text("message"), e.text("step_id")));
    }

    /** Console 規則產生並持久化的告警（{@code origin=CONSOLE}，id＝{@code <seq>.<sub>}）。 */
    static Frame consoleAlert(Alert a, Instant ts) {
        return new Frame(Kind.LOGS, a.eventSeq(), a.eventSub(), "alert", new AlertEventData(a.eventSeq(), a.eventSub(),
                ts.toString(), "CONSOLE", a.id(), a.rule().name(), null, a.severity().name(), a.subject(),
                a.message(), null));
    }

    /** 連線層的暫態告警（{@code BRIDGE_UNREACHABLE}／{@code BRIDGE_RUN_UNKNOWN}）：不持久化、不帶 {@code id:} 行。 */
    static Frame connectionAlert(int anchorSeq, String code, String message, Instant ts) {
        return new Frame(Kind.LOGS, anchorSeq, Frame.NO_ID, "alert", new AlertEventData(anchorSeq, null, ts.toString(),
                "CONSOLE", null, null, code, "WARNING", null, message, null));
    }

    static Frame review(ReviewRequest r, ReviewView view) {
        return new Frame(Kind.LOGS, r.eventSeq(), r.eventSub(), "review-request",
                new ReviewRequestEventData(r.eventSeq(), r.eventSub(), r.requestedAt().toString(), view));
    }

    // ── /metrics ───────────────────────────────────────────────────────────────

    static Frame progress(int seq, int sub, String ts, BridgeStatus status, int completed, int total,
                          CurrentStepView current) {
        double pct = total <= 0 ? 0.0 : round1(completed * 100.0 / total);
        return new Frame(Kind.METRICS, seq, sub, "progress-update", new ProgressUpdateEventData(seq, ts, status.fold(),
                status, completed, total, pct, current));
    }

    static Frame token(int seq, int sub, String ts, long tokensUsed, long delta, double contextPct, Long budget,
                       java.util.UUID taskId) {
        Double usage = budget == null || budget <= 0 ? null : round1(tokensUsed * 100.0 / budget);
        return new Frame(Kind.METRICS, seq, sub, "token-update", new TokenUpdateEventData(seq, ts, tokensUsed, delta,
                contextPct, budget, usage, taskId));
    }

    static Frame metric(int seq, int sub, String ts, int completed, int failed, int total, int retriedTasks,
                        double averageRetryCount, long totalTokens, Long budget, long elapsedSec) {
        Double usage = budget == null || budget <= 0 ? null : round1(totalTokens * 100.0 / budget);
        return new Frame(Kind.METRICS, seq, sub, "metric-update", new MetricUpdateEventData(seq, sub, ts, completed,
                failed, total, retriedTasks, averageRetryCount, totalTokens, usage, elapsedSec));
    }

    // ── 其他 ───────────────────────────────────────────────────────────────────

    /** 審核項的視圖：任務／目標名稱取自凍結的 DAG 節點標籤（不用再查資料庫）。 */
    static ReviewView reviewView(ReviewRequest r, DagSnapshot dag) {
        String taskName = r.taskId() == null ? null : dag.taskById(r.taskId()).map(Node::label).orElse(null);
        String goalName = r.goalId() == null ? null : dag.goalById(r.goalId()).map(Node::label).orElse(null);
        return new ReviewView(r.id(), r.runId(), r.kind(), r.status(), r.stepRowId(), r.taskId(), r.goalId(), taskName,
                goalName, r.reason(), r.requestedAt(), r.decidedBy(), r.decidedAt(), r.comment(),
                ReviewGatePolicy.allowedDecisions(r.kind(), r.taskId() != null));
    }

    static double round1(double value) {
        return BigDecimal.valueOf(value).setScale(1, RoundingMode.HALF_UP).doubleValue();
    }

    static double round2(double value) {
        return BigDecimal.valueOf(value).setScale(2, RoundingMode.HALF_UP).doubleValue();
    }
}
