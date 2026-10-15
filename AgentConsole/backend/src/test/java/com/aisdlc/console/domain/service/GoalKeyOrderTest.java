package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedGoal;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** confirm 的落庫順序：被依賴的目標先存（goal_dependencies 有外鍵），同層依陣列順序（穩定）。 */
class GoalKeyOrderTest {

    private static ParsedGoal goal(String key, String... deps) {
        return new ParsedGoal(key, key, "", "c", 0, List.of(deps), List.of());
    }

    @Test
    void dependenciesComeFirstEvenWhenTheyAppearLaterInTheArray() {
        List<ParsedGoal> goals = List.of(goal("a", "c"), goal("b"), goal("c", "b"));
        assertThat(GoalKeyOrder.dependencyFirstIndexes(goals)).containsExactly(1, 2, 0);
    }

    @Test
    void independentGoalsKeepTheArrayOrder() {
        List<ParsedGoal> goals = List.of(goal("a"), goal("b"), goal("c"));
        assertThat(GoalKeyOrder.dependencyFirstIndexes(goals)).containsExactly(0, 1, 2);
    }

    @Test
    void aChainAndADiamondAreOrderedTopologically() {
        List<ParsedGoal> goals = List.of(goal("d", "b", "c"), goal("b", "a"), goal("c", "a"), goal("a"));
        List<Integer> order = GoalKeyOrder.dependencyFirstIndexes(goals);
        assertThat(order).hasSize(4);
        assertThat(order.indexOf(3)).isLessThan(order.indexOf(1));
        assertThat(order.indexOf(3)).isLessThan(order.indexOf(2));
        assertThat(order.indexOf(1)).isLessThan(order.indexOf(0));
        assertThat(order.indexOf(2)).isLessThan(order.indexOf(0));
    }

    @Test
    void anInvalidCyclicInputReturnsOnlyWhatCanBePlacedInsteadOfLoopingForever() {
        List<ParsedGoal> goals = List.of(goal("a", "b"), goal("b", "a"), goal("c"));
        assertThat(GoalKeyOrder.dependencyFirstIndexes(goals)).containsExactly(2);
    }
}
