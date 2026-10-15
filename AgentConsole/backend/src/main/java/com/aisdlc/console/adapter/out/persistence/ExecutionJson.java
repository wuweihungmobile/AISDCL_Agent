package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.domain.model.execution.DagSnapshot;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Edge;
import com.aisdlc.console.domain.model.execution.DagSnapshot.EdgeKind;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Node;
import com.aisdlc.console.domain.model.execution.DagSnapshot.NodeKind;
import com.aisdlc.console.domain.model.execution.RunLimits;
import com.aisdlc.console.domain.model.execution.RunScope;
import com.aisdlc.console.domain.model.execution.ScopeMode;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * {@code execution_runs.scope}／{@code dag}（JSONB）與 {@code checkpoints.state_snapshot} 的 JSON 互轉
 * （domain 不依賴 JSON 函式庫，轉換放在 persistence 介面卡；JSON 形狀見契約 §1.2.1、§3.4.4）。
 */
final class ExecutionJson {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final TypeReference<Map<String, Object>> OBJECT = new TypeReference<>() { };

    private ExecutionJson() {
    }

    static String scopeToJson(RunScope scope) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("mode", scope.mode().name());
        map.put("goalIds", scope.goalIds().stream().map(UUID::toString).toList());
        map.put("taskIds", scope.taskIds().stream().map(UUID::toString).toList());
        if (!scope.limits().isEmpty()) {
            Map<String, Object> limits = new LinkedHashMap<>();
            if (scope.limits().taskTokens() != null) {
                limits.put("taskTokens", scope.limits().taskTokens());
            }
            if (scope.limits().goalTokens() != null) {
                limits.put("goalTokens", scope.limits().goalTokens());
            }
            map.put("limits", limits);
        }
        if (scope.followUpOfRunId() != null) {
            map.put("followUpOfRunId", scope.followUpOfRunId().toString());
        }
        return JSON.writeValueAsString(map);
    }

    static RunScope scopeFromJson(String json) {
        Map<String, Object> map = parse(json);
        ScopeMode mode = "SELECTED".equals(map.get("mode")) ? ScopeMode.SELECTED : ScopeMode.ALL;
        Map<String, Object> limits = asMap(map.get("limits"));
        RunLimits runLimits = new RunLimits(asLong(limits.get("taskTokens")), asLong(limits.get("goalTokens")));
        Object followUp = map.get("followUpOfRunId");
        return new RunScope(mode, uuids(map.get("goalIds")), uuids(map.get("taskIds")), runLimits,
                followUp == null ? null : UUID.fromString(followUp.toString()));
    }

    static String dagToJson(DagSnapshot dag) {
        List<Map<String, Object>> nodes = new ArrayList<>();
        for (Node node : dag.nodes()) {
            Map<String, Object> map = new LinkedHashMap<>();
            map.put("id", node.id().toString());
            map.put("kind", node.kind().name());
            map.put("label", node.label());
            if (node.goalId() != null) {
                map.put("goalId", node.goalId().toString());
            }
            if (node.stepId() != null) {
                map.put("stepId", node.stepId());
            }
            map.put("sequence", node.sequence());
            nodes.add(map);
        }
        List<Map<String, Object>> edges = new ArrayList<>();
        for (Edge edge : dag.edges()) {
            Map<String, Object> map = new LinkedHashMap<>();
            map.put("from", edge.from().toString());
            map.put("to", edge.to().toString());
            map.put("kind", edge.kind().name());
            edges.add(map);
        }
        Map<String, Object> root = new LinkedHashMap<>();
        root.put("nodes", nodes);
        root.put("edges", edges);
        return JSON.writeValueAsString(root);
    }

    static DagSnapshot dagFromJson(String json) {
        if (json == null || json.isBlank()) {
            return DagSnapshot.EMPTY;
        }
        Map<String, Object> root = parse(json);
        List<Node> nodes = new ArrayList<>();
        for (Object item : asList(root.get("nodes"))) {
            Map<String, Object> map = asMap(item);
            Object goalId = map.get("goalId");
            nodes.add(new Node(UUID.fromString(map.get("id").toString()), NodeKind.valueOf(map.get("kind").toString()),
                    map.get("label") == null ? "" : map.get("label").toString(),
                    goalId == null ? null : UUID.fromString(goalId.toString()),
                    map.get("stepId") == null ? null : map.get("stepId").toString(),
                    map.get("sequence") instanceof Number n ? n.intValue() : 0));
        }
        List<Edge> edges = new ArrayList<>();
        for (Object item : asList(root.get("edges"))) {
            Map<String, Object> map = asMap(item);
            edges.add(new Edge(UUID.fromString(map.get("from").toString()), UUID.fromString(map.get("to").toString()),
                    EdgeKind.valueOf(map.get("kind").toString())));
        }
        return new DagSnapshot(nodes, edges);
    }

    /** {@code state_snapshot} 內的 {@code step_idx}（缺則 0）。 */
    static int snapshotStepIdx(String stateSnapshot) {
        return parse(stateSnapshot).get("step_idx") instanceof Number n ? n.intValue() : 0;
    }

    static String snapshotStepId(String stateSnapshot) {
        Object value = parse(stateSnapshot).get("step_id");
        return value == null ? "" : value.toString();
    }

    static List<String> snapshotCompletedStepIds(String stateSnapshot) {
        return asList(parse(stateSnapshot).get("completed_step_ids")).stream().map(Object::toString).toList();
    }

    private static Map<String, Object> parse(String json) {
        return json == null || json.isBlank() ? Map.of() : JSON.readValue(json, OBJECT);
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> asMap(Object value) {
        return value instanceof Map<?, ?> map ? (Map<String, Object>) map : Map.of();
    }

    private static List<?> asList(Object value) {
        return value instanceof List<?> list ? list : List.of();
    }

    private static List<UUID> uuids(Object value) {
        return asList(value).stream().map(o -> UUID.fromString(o.toString())).toList();
    }

    private static Long asLong(Object value) {
        return value instanceof Number n ? Long.valueOf(n.longValue()) : null;
    }
}
