package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.DagNodeView;
import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.DagView;
import com.aisdlc.console.domain.model.execution.DagSnapshot;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * DAG 圖（契約 §1.2.8）：節點與邊在建立批次時凍結於 {@code execution_runs.dag}，每個節點的 {@code status} 於讀取時疊加
 * 目標／任務的<b>現況</b>（歷史批次也是現況，見 {@code statusAsOf}）。
 */
@Schema(name = "DagResponse")
public record DagResponse(
        @NotNull UUID runId,
        @NotNull List<Node> nodes,
        @NotNull List<Edge> edges,
        @NotNull @Schema(description = "節點 status 的取值時間（現況，不是該批次當時）") Instant statusAsOf) {

    /** DAG 節點：GOAL（目標序）或 TASK（展平後的位置，1 起算，等於 Bridge 的 step_number）。 */
    @Schema(name = "DagNode")
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Node(
            @NotNull @Schema(description = "目標或任務的 UUID") UUID id,
            @NotNull @Schema(allowableValues = {"GOAL", "TASK"}) String kind,
            @NotNull String label,
            @NotNull @Schema(description = "GOAL＝PENDING／IN_PROGRESS／COMPLETED／FAILED／SKIPPED；TASK＝十一態（現況疊加）")
            String status,
            @Schema(description = "TASK 節點的所屬目標") UUID goalId,
            @Schema(description = "TASK 節點在該批次 playbook 的 step_id") String stepId,
            @Schema(description = "執行順序（GOAL＝目標序；TASK＝展平後的位置，1 起算）") Integer sequence) {

        static Node from(DagNodeView v) {
            return new Node(v.id(), v.kind().name(), v.label(), v.status(), v.goalId(), v.stepId(), v.sequence());
        }
    }

    /** DAG 邊：DEPENDENCY（前置目標 → 依賴者）或 CONTAINS（目標 → 其任務）。 */
    @Schema(name = "DagEdge")
    public record Edge(
            @NotNull UUID from,
            @NotNull UUID to,
            @NotNull @Schema(allowableValues = {"DEPENDENCY", "CONTAINS"},
                    description = "DEPENDENCY＝目標前置依賴（from＝前置 → to＝依賴者）；CONTAINS＝目標包含任務") String kind) {

        static Edge from(DagSnapshot.Edge e) {
            return new Edge(e.from(), e.to(), e.kind().name());
        }
    }

    public static DagResponse from(DagView v) {
        return new DagResponse(v.runId(), v.nodes().stream().map(Node::from).toList(),
                v.edges().stream().map(Edge::from).toList(), v.statusAsOf());
    }
}
