package com.aisdlc.console.domain.model.execution;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * 批次建立時凍結的 DAG 結構（{@code execution_runs.dag}；契約 §3.4.4）：只含結構、不含狀態（狀態在讀取時疊加現況）。
 *
 * <p>節點：{@code GOAL}（{@code sequence}＝目標序）與 {@code TASK}（{@code goalId}、{@code stepId}、{@code sequence}＝展平後位置，
 * 1 起算，等於 Bridge 的 {@code step_number}）。邊：{@code DEPENDENCY}（前置目標 → 依賴者，只含範圍內的目標）與
 * {@code CONTAINS}（目標 → 其任務）。
 */
public record DagSnapshot(List<Node> nodes, List<Edge> edges) {

    public enum NodeKind { GOAL, TASK }

    public enum EdgeKind { DEPENDENCY, CONTAINS }

    public record Node(UUID id, NodeKind kind, String label, UUID goalId, String stepId, int sequence) {
    }

    public record Edge(UUID from, UUID to, EdgeKind kind) {
    }

    public DagSnapshot {
        nodes = nodes == null ? List.of() : List.copyOf(nodes);
        edges = edges == null ? List.of() : List.copyOf(edges);
    }

    public static final DagSnapshot EMPTY = new DagSnapshot(List.of(), List.of());

    /** TASK 節點，依 {@code sequence} 升冪（＝playbook 的步驟順序）。 */
    public List<Node> taskNodes() {
        return nodes.stream().filter(n -> n.kind() == NodeKind.TASK)
                .sorted(java.util.Comparator.comparingInt(Node::sequence)).toList();
    }

    public List<Node> goalNodes() {
        return nodes.stream().filter(n -> n.kind() == NodeKind.GOAL)
                .sorted(java.util.Comparator.comparingInt(Node::sequence)).toList();
    }

    public int totalSteps() {
        return (int) nodes.stream().filter(n -> n.kind() == NodeKind.TASK).count();
    }

    /** 以 playbook 的 step_id（例：{@code G1-T2}）找 TASK 節點。 */
    public Optional<Node> taskByStepId(String stepId) {
        if (stepId == null) {
            return Optional.empty();
        }
        return nodes.stream().filter(n -> n.kind() == NodeKind.TASK && stepId.equals(n.stepId())).findFirst();
    }

    /** 以步驟位置（1 起算）找 TASK 節點。 */
    public Optional<Node> taskAtPosition(int position) {
        return nodes.stream().filter(n -> n.kind() == NodeKind.TASK && n.sequence() == position).findFirst();
    }

    public Optional<Node> taskById(UUID taskId) {
        return nodes.stream().filter(n -> n.kind() == NodeKind.TASK && n.id().equals(taskId)).findFirst();
    }

    public Optional<Node> goalById(UUID goalId) {
        return nodes.stream().filter(n -> n.kind() == NodeKind.GOAL && n.id().equals(goalId)).findFirst();
    }

    /** 某目標在本批次範圍內的 TASK 節點（依位置升冪）。 */
    public List<Node> tasksOfGoal(UUID goalId) {
        return taskNodes().stream().filter(n -> goalId.equals(n.goalId())).toList();
    }

    /** 該步驟是否為其所屬目標在本批次範圍內的最後一步。 */
    public boolean isLastOfGoal(int position) {
        Optional<Node> node = taskAtPosition(position);
        if (node.isEmpty()) {
            return false;
        }
        List<Node> siblings = tasksOfGoal(node.get().goalId());
        return !siblings.isEmpty() && siblings.get(siblings.size() - 1).sequence() == position;
    }

    /** 某目標在本批次範圍內的第一個步驟位置（沒有 TASK 節點回 empty）。 */
    public Optional<Integer> firstPositionOfGoal(UUID goalId) {
        List<Node> siblings = tasksOfGoal(goalId);
        return siblings.isEmpty() ? Optional.empty() : Optional.of(siblings.get(0).sequence());
    }
}
