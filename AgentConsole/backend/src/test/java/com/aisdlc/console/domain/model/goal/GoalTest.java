package com.aisdlc.console.domain.model.goal;

import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.IllegalStateTransitionException;
import com.aisdlc.console.domain.exception.ValidationException;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class GoalTest {

    private static final Instant T0 = Instant.parse("2026-10-14T10:00:00Z");
    private static final Instant T1 = T0.plus(Duration.ofMinutes(5));
    private static final UUID PROJECT = UUID.fromString("11111111-1111-1111-1111-111111111111");

    private static Goal newGoal(boolean draft, List<UUID> deps) {
        return Goal.create(PROJECT, new NewGoal("建立基礎架構", "說明", "- [ ] 全部通過", deps, draft), 2, T0);
    }

    @Test
    void createStartsPendingWithGivenSortOrderAndManualGoalIsSignedOff() {
        Goal g = newGoal(false, null);
        assertThat(g.status()).isEqualTo(GoalStatus.PENDING);
        assertThat(g.sortOrder()).isEqualTo(2);
        assertThat(g.signedOff()).isTrue();
        assertThat(g.projectId()).isEqualTo(PROJECT);
        assertThat(g.dependsOn()).isEmpty();
        assertThat(g.deleted()).isFalse();
    }

    @Test
    void draftGoalIsNotSignedOff() {
        assertThat(newGoal(true, null).signedOff()).isFalse();
    }

    @Test
    void createRequiresNameAndPassCriteria() {
        assertThatThrownBy(() -> Goal.create(PROJECT, new NewGoal(" ", null, "", null, false), 0, T0))
                .isInstanceOfSatisfying(ValidationException.class, e -> assertThat(e.violations())
                        .extracting("field").containsExactlyInAnyOrder("name", "passCriteria"));
    }

    @Test
    void createDeduplicatesDependenciesKeepingOrder() {
        UUID a = UUID.randomUUID();
        UUID b = UUID.randomUUID();
        Goal g = newGoal(false, List.of(a, b, a));
        assertThat(g.dependsOn()).containsExactly(a, b);
    }

    @Test
    void updateRejectsADependencyOnItself() {
        Goal g = newGoal(false, null);
        assertThatThrownBy(() -> g.update(new GoalUpdate(null, null, null, null, List.of(g.id())), T1))
                .isInstanceOfSatisfying(ValidationException.class, e -> {
                    assertThat(e.reason()).isEqualTo("自依賴");
                    assertThat(e.violations().get(0).field()).isEqualTo("dependsOn");
                });
        assertThat(g.dependsOn()).isEmpty();
    }

    @Test
    void updateReplacesTheWholeDependencySetAndEmptyListClearsIt() {
        UUID a = UUID.randomUUID();
        UUID b = UUID.randomUUID();
        Goal g = newGoal(false, List.of(a));
        g.update(new GoalUpdate(null, null, null, null, List.of(b)), T1);
        assertThat(g.dependsOn()).containsExactly(b);
        g.update(new GoalUpdate(null, null, null, null, List.of()), T1);
        assertThat(g.dependsOn()).isEmpty();
        g.update(new GoalUpdate(null, null, null, null, null), T1);
        assertThat(g.dependsOn()).as("null＝不變").isEmpty();
    }

    @Test
    void updateChangesProvidedFieldsOnlyAndTouchesUpdatedAtOnlyWhenChanged() {
        Goal g = newGoal(false, null);
        g.update(new GoalUpdate(null, null, null, null, null), T1);
        assertThat(g.updatedAt()).isEqualTo(T0);
        g.update(new GoalUpdate("新名稱", "", "新標準", 5, null), T1);
        assertThat(g.name()).isEqualTo("新名稱");
        assertThat(g.description()).isNull();
        assertThat(g.passCriteria()).isEqualTo("新標準");
        assertThat(g.sortOrder()).isEqualTo(5);
        assertThat(g.updatedAt()).isEqualTo(T1);
    }

    @Test
    void updateRejectsNegativeSortOrderAndBlankName() {
        Goal g = newGoal(false, null);
        assertThatThrownBy(() -> g.update(new GoalUpdate(" ", null, null, -1, null), T1))
                .isInstanceOfSatisfying(ValidationException.class, e -> assertThat(e.violations())
                        .extracting("field").containsExactlyInAnyOrder("name", "sortOrder"));
    }

    @Test
    void moveToChangesSortOrderOnly() {
        Goal g = newGoal(false, null);
        g.moveTo(2, T1);
        assertThat(g.updatedAt()).as("位置沒變不動 updatedAt").isEqualTo(T0);
        g.moveTo(0, T1);
        assertThat(g.sortOrder()).isZero();
        assertThat(g.updatedAt()).isEqualTo(T1);
    }

    @Test
    void statusTransitionsFollowAppendixB2() {
        Goal g = newGoal(false, null);
        g.transitionTo(GoalStatus.IN_PROGRESS, T1);
        g.transitionTo(GoalStatus.FAILED, T1);
        g.transitionTo(GoalStatus.PENDING, T1);
        assertThat(g.status()).isEqualTo(GoalStatus.PENDING);
        assertThatThrownBy(() -> g.transitionTo(GoalStatus.COMPLETED, T1))
                .isInstanceOf(IllegalStateTransitionException.class);
    }

    @Test
    void signoffRulesMatchTheProjectOnes() {
        Goal g = newGoal(true, null);
        assertThatThrownBy(() -> g.signoff(" ", T1)).isInstanceOf(ValidationException.class);
        g.signoff("Bob", T1);
        assertThat(g.signedOff()).isTrue();
        assertThat(g.signedOffBy()).isEqualTo("Bob");
        assertThat(g.signedOffAt()).isEqualTo(T1);
        assertThatThrownBy(() -> g.signoff("Eve", T1)).isInstanceOf(ConflictException.class);
    }

    @Test
    void softDeleteMarksDeletedWithoutChangingStatus() {
        Goal g = newGoal(false, null);
        g.softDelete(T1);
        assertThat(g.deleted()).isTrue();
        assertThat(g.status()).isEqualTo(GoalStatus.PENDING);
    }
}
