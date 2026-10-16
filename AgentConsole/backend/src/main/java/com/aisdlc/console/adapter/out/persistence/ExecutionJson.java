package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.domain.model.execution.DagSnapshot;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Edge;
import com.aisdlc.console.domain.model.execution.DagSnapshot.EdgeKind;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Node;
import com.aisdlc.console.domain.model.execution.DagSnapshot.NodeKind;
import com.aisdlc.console.domain.model.execution.EngineCapabilities;
import com.aisdlc.console.domain.model.execution.EngineCapabilityState;
import com.aisdlc.console.domain.model.execution.RunLimits;
import com.aisdlc.console.domain.model.execution.RunScope;
import com.aisdlc.console.domain.model.execution.ScopeMode;
import tools.jackson.core.JacksonException;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * {@code execution_runs.scope}／{@code dag}／{@code engine_capabilities}（JSONB）與 {@code checkpoints.state_snapshot} 的 JSON 互轉
 * （domain 不依賴 JSON 函式庫，轉換放在 persistence 介面卡；JSON 形狀見契約 §1.2.1、§3.4.2、§3.4.4）。
 */
final class ExecutionJson {

    /** {@code engine_capabilities} 的兩個鍵（契約 §0.5 V10 寫入規則③：固定、不可改名）。 */
    static final String AUTO_MUTATION_KEY = "autoMutation";
    static final String SELF_EVOLUTION_KEY = "selfEvolution";

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

    /**
     * {@code execution_runs.engine_capabilities}（JSONB；V10）的寫出：鍵固定為 {@code autoMutation}、{@code selfEvolution}，
     * 值為 {@link EngineCapabilityState} 的名稱。{@code null}（沒有能力狀態）寫成 SQL NULL，不寫 {@code "null"} 文字。
     */
    static String capabilitiesToJson(EngineCapabilities capabilities) {
        if (capabilities == null) {
            return null;
        }
        Map<String, Object> map = new LinkedHashMap<>();
        if (capabilities.autoMutation() != null) {
            map.put(AUTO_MUTATION_KEY, capabilities.autoMutation().name());
        }
        if (capabilities.selfEvolution() != null) {
            map.put(SELF_EVOLUTION_KEY, capabilities.selfEvolution().name());
        }
        return JSON.writeValueAsString(map);
    }

    /**
     * 讀回時缺鍵或值不認得一律當成「該鍵缺席」（前向相容，契約 §0.5 V10 寫入規則③），不丟例外；兩個鍵都缺席或本文不是
     * JSON 物件＝整個欄位當成沒有值（回 null），前端不顯示晶片、也不猜測。
     */
    static EngineCapabilities capabilitiesFromJson(String json) {
        if (json == null || json.isBlank()) {
            return null;
        }
        Map<String, Object> map;
        try {
            map = parse(json);
        } catch (JacksonException e) {
            return null;
        }
        EngineCapabilityState autoMutation = EngineCapabilityState.parse(map.get(AUTO_MUTATION_KEY)).orElse(null);
        EngineCapabilityState selfEvolution = EngineCapabilityState.parse(map.get(SELF_EVOLUTION_KEY)).orElse(null);
        return autoMutation == null && selfEvolution == null ? null
                : new EngineCapabilities(autoMutation, selfEvolution);
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
