package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.exception.ValidationException;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Deque;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

/**
 * 目標依賴圖的 Kahn 拓撲排序與環偵測（PRD §5.1.2／§6.2：新增依賴前先試算，成環則拒絕）。
 *
 * <p>圖的表示：{@code dependsOn.get(n)} ＝ n 的前置依賴（n 必須等它們完成）。邊方向為「被依賴者 → 依賴者」，
 * 因此拓撲序中被依賴者排在前面。輸入 map 的鍵與值中出現的所有 id 都視為節點（值中出現而不在鍵中的節點
 * 視為「沒有任何前置依賴」）。
 *
 * <p>本類別不可變、無狀態、純 Java；輸入順序決定輸出的穩定順序，方便測試與穩定呈現。
 */
public final class DagService {

    /** 依賴成環時 {@link ValidationException#reason()} 的固定字樣（任務書指定）。 */
    public static final String CYCLE_REASON = "依賴成環";

    private DagService() {
    }

    /**
     * Kahn 演算法：回傳拓撲序（沒有前置依賴者在前）。
     *
     * @throws ValidationException 圖含環時（reason＝{@link #CYCLE_REASON}，details.cycle 為環路 id 清單）
     */
    public static List<UUID> topologicalOrder(Map<UUID, ? extends Collection<UUID>> dependsOn) {
        Run run = run(dependsOn);
        if (!run.remaining.isEmpty()) {
            throw cycleException(extractCycle(run));
        }
        return run.order;
    }

    /**
     * 分層 Kahn（契約 §1.2.1 的範圍解析）：每一輪取出「目前全部前置依賴都已排定」的節點（同一層），
     * 層內依 {@code tieBreak} 排序後接在結果後面；下一層以此類推。{@code tieBreak} 為 null 時層內保持輸入順序。
     * 這是 {@code execution.dagSchedulerStrategy} 的三種策略（TOPOLOGICAL／PRIORITY／SHORTEST_FIRST）共用的骨架：
     * 策略只決定同層的比較器。
     *
     * @throws ValidationException 圖含環時（reason＝{@link #CYCLE_REASON}）
     */
    public static List<UUID> layeredOrder(Map<UUID, ? extends Collection<UUID>> dependsOn,
                                          java.util.Comparator<UUID> tieBreak) {
        Map<UUID, Set<UUID>> deps = new LinkedHashMap<>();
        for (Map.Entry<UUID, ? extends Collection<UUID>> entry : dependsOn.entrySet()) {
            deps.computeIfAbsent(entry.getKey(), k -> new LinkedHashSet<>());
            for (UUID dependency : entry.getValue()) {
                deps.computeIfAbsent(dependency, k -> new LinkedHashSet<>());
                deps.get(entry.getKey()).add(dependency);
            }
        }
        List<UUID> order = new ArrayList<>();
        Set<UUID> placed = new LinkedHashSet<>();
        Set<UUID> remaining = new LinkedHashSet<>(deps.keySet());
        while (!remaining.isEmpty()) {
            List<UUID> layer = new ArrayList<>();
            for (UUID node : remaining) {
                if (placed.containsAll(deps.get(node))) {
                    layer.add(node);
                }
            }
            if (layer.isEmpty()) {
                throw cycleException(extractCycle(new Run(deps, order, remaining)));
            }
            if (tieBreak != null) {
                layer.sort(tieBreak);
            }
            order.addAll(layer);
            placed.addAll(layer);
            layer.forEach(remaining::remove);
        }
        return order;
    }

    /**
     * 找出一條實際的環路；無環回 empty。回傳的清單首尾相同（例：[A, B, C, A] 表示 A 依賴 B、B 依賴 C、C 依賴 A）。
     */
    public static Optional<List<UUID>> findCycle(Map<UUID, ? extends Collection<UUID>> dependsOn) {
        Run run = run(dependsOn);
        if (run.remaining.isEmpty()) {
            return Optional.empty();
        }
        return Optional.of(extractCycle(run));
    }

    /** 成環即丟 {@link ValidationException}（400）；無環靜默返回。 */
    public static void requireAcyclic(Map<UUID, ? extends Collection<UUID>> dependsOn) {
        findCycle(dependsOn).ifPresent(cycle -> {
            throw cycleException(cycle);
        });
    }

    private static ValidationException cycleException(List<UUID> cycle) {
        List<String> ids = cycle.stream().map(UUID::toString).toList();
        return ValidationException.of("dependsOn",
                "目標依賴成環：" + String.join(" -> ", ids),
                CYCLE_REASON,
                Map.of("cycle", ids));
    }

    private static Run run(Map<UUID, ? extends Collection<UUID>> dependsOn) {
        Map<UUID, Set<UUID>> deps = new LinkedHashMap<>();
        for (Map.Entry<UUID, ? extends Collection<UUID>> entry : dependsOn.entrySet()) {
            deps.computeIfAbsent(entry.getKey(), k -> new LinkedHashSet<>());
            for (UUID dependency : entry.getValue()) {
                deps.computeIfAbsent(dependency, k -> new LinkedHashSet<>());
                deps.get(entry.getKey()).add(dependency);
            }
        }
        Map<UUID, List<UUID>> dependents = new HashMap<>();
        Map<UUID, Integer> indegree = new LinkedHashMap<>();
        for (Map.Entry<UUID, Set<UUID>> entry : deps.entrySet()) {
            indegree.put(entry.getKey(), entry.getValue().size());
            for (UUID dependency : entry.getValue()) {
                dependents.computeIfAbsent(dependency, k -> new ArrayList<>()).add(entry.getKey());
            }
        }
        Deque<UUID> ready = new ArrayDeque<>();
        indegree.forEach((node, degree) -> {
            if (degree == 0) {
                ready.add(node);
            }
        });
        List<UUID> order = new ArrayList<>();
        while (!ready.isEmpty()) {
            UUID node = ready.poll();
            order.add(node);
            for (UUID dependent : dependents.getOrDefault(node, List.of())) {
                int degree = indegree.merge(dependent, -1, Integer::sum);
                if (degree == 0) {
                    ready.add(dependent);
                }
            }
        }
        Set<UUID> remaining = new LinkedHashSet<>(deps.keySet());
        remaining.removeAll(order);
        return new Run(deps, order, remaining);
    }

    /**
     * Kahn 結束後的殘餘節點可能包含「環上的點」與「環下游的點」。每個殘餘節點至少有一個同樣殘餘的前置依賴
     * （否則它的入度早已歸零），沿著「殘餘的前置依賴」一路走必然在有限步內回到走過的節點，那一段就是環。
     */
    private static List<UUID> extractCycle(Run run) {
        Map<UUID, Integer> position = new HashMap<>();
        List<UUID> path = new ArrayList<>();
        UUID current = run.remaining.iterator().next();
        while (!position.containsKey(current)) {
            position.put(current, path.size());
            path.add(current);
            UUID next = null;
            for (UUID dependency : run.deps.get(current)) {
                if (run.remaining.contains(dependency)) {
                    next = dependency;
                    break;
                }
            }
            current = next;
        }
        List<UUID> cycle = new ArrayList<>(path.subList(position.get(current), path.size()));
        cycle.add(current);
        return cycle;
    }

    private record Run(Map<UUID, Set<UUID>> deps, List<UUID> order, Set<UUID> remaining) {
    }
}
