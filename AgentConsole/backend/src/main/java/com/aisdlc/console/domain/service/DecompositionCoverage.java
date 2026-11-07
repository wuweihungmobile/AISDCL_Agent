package com.aisdlc.console.domain.service;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 拆解的覆蓋對映（PRD FR-R2P-14、AC-R2P-14-2；D-121：console-api 不重算 Bridge 的對映，只讀拆解 artifact 內容並判定「簽核能不能過」）。純函式、無 I/O，
 * ArchUnit 判為純 Java。
 *
 * <p>輸入是拆解 artifact 的 JSON 全文（{@code task_decomposition.json}，PRD §5.1.6 形狀）：優先取 Bridge 寫入的 {@code coverage{total,covered,uncovered[]}}
 * （Bridge 對凍結 PRD 的 AC 全集確定性算出，D-94）；沒有 {@code coverage} 時退而求其次——AC 全集取 {@code ac_universe}（若有），已覆蓋集合取全部 task 的
 * {@code covers_ac}。豁免（{@code waivers[{ac,reason}]}）涵蓋的未覆蓋 AC 不阻擋簽核；每個豁免須有非空白理由、AC 須確實在未覆蓋清單內。
 */
public final class DecompositionCoverage {

    /** 一條豁免：AC 編號與人工理由。 */
    public record Waiver(String ac, String reason) {
    }

    /** 覆蓋結果：{@code uncovered} 為依出現順序的未覆蓋 AC（尚未扣除豁免）。 */
    public record Result(int total, int covered, List<String> uncovered) {

        public Result {
            uncovered = List.copyOf(uncovered);
        }
    }

    private DecompositionCoverage() {
    }

    /** 讀拆解內容算覆蓋；{@code content} 為 null（尚無 artifact）回全 0。 */
    public static Result of(Map<String, Object> content) {
        if (content == null) {
            return new Result(0, 0, List.of());
        }
        if (content.get("coverage") instanceof Map<?, ?> coverage) {
            List<String> uncovered = strings(coverage.get("uncovered"));
            int total = number(coverage.get("total"), -1);
            int covered = number(coverage.get("covered"), -1);
            if (total >= 0) {
                return new Result(total, covered >= 0 ? covered : Math.max(0, total - uncovered.size()), uncovered);
            }
        }
        Set<String> universe = new LinkedHashSet<>(strings(content.get("ac_universe")));
        Set<String> covered = new LinkedHashSet<>();
        if (content.get("goals") instanceof List<?> goals) {
            for (Object goal : goals) {
                if (goal instanceof Map<?, ?> g && g.get("tasks") instanceof List<?> tasks) {
                    for (Object task : tasks) {
                        if (task instanceof Map<?, ?> t) {
                            covered.addAll(strings(t.get("covers_ac")));
                        }
                    }
                }
            }
        }
        if (universe.isEmpty()) {
            universe.addAll(covered);
        }
        List<String> uncovered = new ArrayList<>();
        for (String ac : universe) {
            if (!covered.contains(ac)) {
                uncovered.add(ac);
            }
        }
        return new Result(universe.size(), universe.size() - uncovered.size(), uncovered);
    }

    /** 扣掉豁免後仍未覆蓋的 AC（空＝可簽核）。理由空白的豁免不算數；不在未覆蓋清單內的豁免被忽略。 */
    public static List<String> stillUncovered(Result result, List<Waiver> waivers) {
        Set<String> waived = new LinkedHashSet<>();
        for (Waiver waiver : waivers == null ? List.<Waiver>of() : waivers) {
            if (waiver != null && waiver.ac() != null && waiver.reason() != null && !waiver.reason().isBlank()) {
                waived.add(waiver.ac());
            }
        }
        List<String> out = new ArrayList<>();
        for (String ac : result.uncovered()) {
            if (!waived.contains(ac)) {
                out.add(ac);
            }
        }
        return out;
    }

    private static List<String> strings(Object value) {
        List<String> out = new ArrayList<>();
        if (value instanceof List<?> list) {
            for (Object item : list) {
                if (item != null) {
                    out.add(item.toString());
                }
            }
        }
        return out;
    }

    private static int number(Object value, int fallback) {
        return value instanceof Number n ? n.intValue() : fallback;
    }
}
