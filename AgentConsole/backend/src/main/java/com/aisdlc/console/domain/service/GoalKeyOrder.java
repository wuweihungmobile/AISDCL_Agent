package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedGoal;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 匯入草案的目標拓撲序（Kahn）：落庫時被依賴的目標必須先存（{@code goal_dependencies} 有外鍵），
 * 所以 confirm 以「依賴在前」的順序建立目標；而每個目標的 {@code sortOrder} 一律取自它在陣列中的位置，與建立順序無關。
 *
 * <p>同一層可同時就緒的目標依陣列順序（穩定）。輸入必須已通過有界閘的 {@code cycle} 閘（無環、無懸空依賴）；
 * 不合法的輸入回傳「能排的部分」，由呼叫端的閘負責先擋下。
 */
public final class GoalKeyOrder {

    private GoalKeyOrder() {
    }

    /** @return 依賴在前的目標索引（對應輸入陣列的位置）。 */
    public static List<Integer> dependencyFirstIndexes(List<ParsedGoal> goals) {
        Map<String, Integer> indexByKey = new HashMap<>();
        for (int i = 0; i < goals.size(); i++) {
            indexByKey.putIfAbsent(goals.get(i).key(), i);
        }
        List<Integer> order = new ArrayList<>();
        Set<Integer> placed = new LinkedHashSet<>();
        boolean progressed = true;
        while (placed.size() < goals.size() && progressed) {
            progressed = false;
            for (int i = 0; i < goals.size(); i++) {
                if (placed.contains(i)) {
                    continue;
                }
                boolean ready = true;
                List<String> deps = goals.get(i).dependsOn() == null ? List.of() : goals.get(i).dependsOn();
                for (String dependency : deps) {
                    Integer dependencyIndex = indexByKey.get(dependency);
                    if (dependencyIndex != null && dependencyIndex != i && !placed.contains(dependencyIndex)) {
                        ready = false;
                        break;
                    }
                }
                if (ready) {
                    placed.add(i);
                    order.add(i);
                    progressed = true;
                }
            }
        }
        return order;
    }
}
