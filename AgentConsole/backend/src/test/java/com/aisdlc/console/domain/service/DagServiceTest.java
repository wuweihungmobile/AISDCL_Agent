package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.exception.ValidationException;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Kahn 拓撲排序與環偵測（PRD §5.1.2／§6.2：新增依賴前先試算，成環則拒絕）。 */
class DagServiceTest {

    private static final UUID A = UUID.fromString("00000000-0000-0000-0000-00000000000a");
    private static final UUID B = UUID.fromString("00000000-0000-0000-0000-00000000000b");
    private static final UUID C = UUID.fromString("00000000-0000-0000-0000-00000000000c");
    private static final UUID D = UUID.fromString("00000000-0000-0000-0000-00000000000d");
    private static final UUID E = UUID.fromString("00000000-0000-0000-0000-00000000000e");

    @Test
    void emptyGraphHasEmptyOrderAndNoCycle() {
        assertThat(DagService.topologicalOrder(Map.of())).isEmpty();
        assertThat(DagService.findCycle(Map.of())).isEmpty();
    }

    @Test
    void chainIsOrderedDependenciesFirst() {
        // C 依賴 B、B 依賴 A
        Map<UUID, Set<UUID>> graph = new LinkedHashMap<>();
        graph.put(C, Set.of(B));
        graph.put(B, Set.of(A));
        graph.put(A, Set.of());
        assertThat(DagService.topologicalOrder(graph)).containsExactly(A, B, C);
    }

    @Test
    void diamondPutsEveryDependencyBeforeItsDependent() {
        Map<UUID, Set<UUID>> graph = new LinkedHashMap<>();
        graph.put(D, Set.of(B, C));
        graph.put(B, Set.of(A));
        graph.put(C, Set.of(A));
        graph.put(A, Set.of());
        List<UUID> order = DagService.topologicalOrder(graph);
        assertThat(order).hasSize(4).containsExactlyInAnyOrder(A, B, C, D);
        assertThat(order.indexOf(A)).isLessThan(order.indexOf(B)).isLessThan(order.indexOf(C));
        assertThat(order.indexOf(B)).isLessThan(order.indexOf(D));
        assertThat(order.indexOf(C)).isLessThan(order.indexOf(D));
    }

    @Test
    void referencedButUndeclaredNodeIsTreatedAsHavingNoDependencies() {
        Map<UUID, Set<UUID>> graph = Map.of(B, Set.of(A));
        assertThat(DagService.topologicalOrder(graph)).containsExactly(A, B);
    }

    @Test
    void disconnectedComponentsAreAllOrdered() {
        Map<UUID, Set<UUID>> graph = new LinkedHashMap<>();
        graph.put(B, Set.of(A));
        graph.put(E, Set.of(D));
        graph.put(C, Set.of());
        List<UUID> order = DagService.topologicalOrder(graph);
        assertThat(order).containsExactlyInAnyOrder(A, B, C, D, E);
        assertThat(order.indexOf(A)).isLessThan(order.indexOf(B));
        assertThat(order.indexOf(D)).isLessThan(order.indexOf(E));
    }

    @Test
    void selfDependencyIsACycleOfLengthOne() {
        Map<UUID, Set<UUID>> graph = Map.of(A, Set.of(A));
        assertThat(DagService.findCycle(graph)).contains(List.of(A, A));
    }

    @Test
    void twoNodeCycleIsDetected() {
        Map<UUID, Set<UUID>> graph = new LinkedHashMap<>();
        graph.put(A, Set.of(B));
        graph.put(B, Set.of(A));
        List<UUID> cycle = DagService.findCycle(graph).orElseThrow();
        assertIsRealCycle(cycle, graph);
        assertThat(cycle).hasSize(3).contains(A, B);
    }

    @Test
    void cycleExtractionIgnoresNodesDownstreamOfTheCycle() {
        // A→B→C→A 成環；D 依賴 A（在環的下游，不屬於環）；E 是環外獨立節點。
        Map<UUID, Set<UUID>> graph = new LinkedHashMap<>();
        graph.put(D, Set.of(A));
        graph.put(E, Set.of());
        graph.put(A, Set.of(B));
        graph.put(B, Set.of(C));
        graph.put(C, Set.of(A));
        List<UUID> cycle = DagService.findCycle(graph).orElseThrow();
        assertIsRealCycle(cycle, graph);
        assertThat(cycle).doesNotContain(D, E);
        assertThat(cycle).hasSize(4);
    }

    @Test
    void requireAcyclicThrowsValidationExceptionCarryingTheCycleIds() {
        Map<UUID, Set<UUID>> graph = new LinkedHashMap<>();
        graph.put(A, Set.of(B));
        graph.put(B, Set.of(A));
        assertThatThrownBy(() -> DagService.requireAcyclic(graph))
                .isInstanceOfSatisfying(ValidationException.class, e -> {
                    assertThat(e.reason()).isEqualTo("依賴成環");
                    assertThat(e.violations()).extracting("field").containsExactly("dependsOn");
                    assertThat(e.details()).containsKey("cycle");
                    @SuppressWarnings("unchecked")
                    List<String> ids = (List<String>) e.details().get("cycle");
                    assertThat(ids).contains(A.toString(), B.toString());
                    assertThat(ids.get(0)).isEqualTo(ids.get(ids.size() - 1));
                });
    }

    @Test
    void requireAcyclicAcceptsAnAcyclicGraph() {
        assertThatCode(() -> DagService.requireAcyclic(Map.of(B, Set.of(A), C, Set.of(A, B))))
                .doesNotThrowAnyException();
    }

    @Test
    void topologicalOrderRefusesACyclicGraph() {
        Map<UUID, Set<UUID>> graph = Map.of(A, Set.of(B), B, Set.of(C), C, Set.of(A));
        assertThatThrownBy(() -> DagService.topologicalOrder(graph)).isInstanceOf(ValidationException.class);
    }

    @Test
    void veryLongChainIsHandledIterativelyWithoutStackOverflow() {
        Map<UUID, Set<UUID>> graph = new HashMap<>();
        UUID previous = null;
        UUID first = null;
        UUID last = null;
        for (int i = 0; i < 20_000; i++) {
            UUID node = UUID.randomUUID();
            graph.put(node, previous == null ? Set.of() : Set.of(previous));
            if (first == null) {
                first = node;
            }
            previous = node;
            last = node;
        }
        List<UUID> order = DagService.topologicalOrder(graph);
        assertThat(order).hasSize(20_000);
        assertThat(order.get(0)).isEqualTo(first);
        assertThat(order.get(order.size() - 1)).isEqualTo(last);
    }

    /** 環必須首尾相同，且每一步都是真實存在的「依賴」邊。 */
    private static void assertIsRealCycle(List<UUID> cycle, Map<UUID, Set<UUID>> graph) {
        assertThat(cycle.get(0)).isEqualTo(cycle.get(cycle.size() - 1));
        for (int i = 0; i < cycle.size() - 1; i++) {
            assertThat(graph.getOrDefault(cycle.get(i), Set.of()))
                    .as("%s 依賴 %s 這條邊必須存在", cycle.get(i), cycle.get(i + 1))
                    .contains(cycle.get(i + 1));
        }
    }
}
