package com.aisdlc.console.domain.model.task;

import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.IllegalStateTransitionException;
import com.aisdlc.console.domain.exception.ValidationException;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class TaskTest {

    private static final Instant T0 = Instant.parse("2026-10-14T10:00:00Z");
    private static final Instant T1 = T0.plus(Duration.ofMinutes(5));
    private static final UUID GOAL = UUID.fromString("22222222-2222-2222-2222-222222222222");

    private static NewTask spec(String command, String regex) {
        return new NewTask("實作 Controller", "說明", "輸出 OK", command, regex, null, null, null, false);
    }

    private static Task taskIn(TaskStatus status) {
        return Task.restore(UUID.randomUUID(), GOAL, "任務", null, "標準", null, null, null, 0, status, null, null,
                1, 3, null, null, true, null, null, false, T0, T0, null, null, null);
    }

    private static TaskUpdate update(String name, String command, String regex, String spec, Integer maxRetries) {
        return new TaskUpdate(name, null, null, maxRetries, command, regex, spec, null, null);
    }

    // ---- 建立 ----

    @Test
    void createStartsPendingWithDefaultsAndManualTaskIsSignedOff() {
        Task t = Task.create(GOAL, spec("pytest -q", "^OK$"), 4, T0);
        assertThat(t.status()).isEqualTo(TaskStatus.PENDING);
        assertThat(t.retryCount()).isZero();
        assertThat(t.maxRetries()).as("PRD：maxRetries 預設 3").isEqualTo(3);
        assertThat(t.sortOrder()).isEqualTo(4);
        assertThat(t.signedOff()).isTrue();
        assertThat(t.evaluatorCommand()).isEqualTo("pytest -q");
        assertThat(t.expectedOutputRegex()).isEqualTo("^OK$");
        assertThat(t.deleted()).isFalse();
    }

    @Test
    void draftTaskIsNotSignedOffAndExplicitMaxRetriesIsKept() {
        Task t = Task.create(GOAL, new NewTask("t", null, "c", null, null, "{\"a\":1}", 500L, 0, true), 0, T0);
        assertThat(t.signedOff()).isFalse();
        assertThat(t.maxRetries()).isZero();
        assertThat(t.estimatedTokens()).isEqualTo(500L);
        assertThat(t.passCriteriaSpec()).isEqualTo("{\"a\":1}");
    }

    @Test
    void createRejectsEvaluatorCommandWithDenyCharsAndListsThem() {
        assertThatThrownBy(() -> Task.create(GOAL, spec("echo a; rm -rf / && echo $HOME", null), 0, T0))
                .isInstanceOfSatisfying(ValidationException.class, e -> {
                    assertThat(e.violations().get(0).field()).isEqualTo("evaluatorCommand");
                    assertThat(e.details().get("violations")).isEqualTo(List.of(";", "&", "$"));
                });
    }

    @Test
    void createRejectsAnUncompilableRegex() {
        assertThatThrownBy(() -> Task.create(GOAL, spec(null, "(unclosed"), 0, T0))
                .isInstanceOfSatisfying(ValidationException.class,
                        e -> assertThat(e.violations().get(0).field()).isEqualTo("expectedOutputRegex"));
    }

    @Test
    void createRejectsTooLongCommandAndNegativeNumbers() {
        assertThatThrownBy(() -> Task.create(GOAL,
                new NewTask("t", null, "c", "x".repeat(1001), null, null, -1L, -2, false), 0, T0))
                .isInstanceOfSatisfying(ValidationException.class, e -> assertThat(e.violations())
                        .extracting("field").containsExactlyInAnyOrder("evaluatorCommand", "estimatedTokens",
                                "maxRetries"));
    }

    @Test
    void createRequiresNameAndPassCriteria() {
        assertThatThrownBy(() -> Task.create(GOAL, new NewTask("", null, " ", null, null, null, null, null, false), 0, T0))
                .isInstanceOfSatisfying(ValidationException.class, e -> assertThat(e.violations())
                        .extracting("field").containsExactlyInAnyOrder("name", "passCriteria"));
    }

    // ---- 更新 ----

    @Test
    void updateAppliesSanitizationJustLikeCreate() {
        Task t = Task.create(GOAL, spec("pytest -q", null), 0, T0);
        assertThatThrownBy(() -> t.update(update(null, "pytest > out.txt", null, null, null), T1))
                .isInstanceOfSatisfying(ValidationException.class,
                        e -> assertThat(e.details().get("violations")).isEqualTo(List.of(">")));
        assertThatThrownBy(() -> t.update(update(null, null, "[", null, null), T1))
                .isInstanceOf(ValidationException.class);
        assertThat(t.evaluatorCommand()).as("驗證失敗不得留下半套修改").isEqualTo("pytest -q");
    }

    @Test
    void updateChangesOnlyProvidedFieldsAndBlankClearsOptionalOnes() {
        Task t = Task.create(GOAL, spec("pytest -q", "^OK$"), 0, T0);
        t.update(update(null, "", "", null, 9), T1);
        assertThat(t.evaluatorCommand()).isNull();
        assertThat(t.expectedOutputRegex()).isNull();
        assertThat(t.maxRetries()).isEqualTo(9);
        assertThat(t.name()).isEqualTo("實作 Controller");
        assertThat(t.updatedAt()).isEqualTo(T1);
    }

    @Test
    void noOpUpdateDoesNotTouchUpdatedAt() {
        Task t = Task.create(GOAL, spec("pytest -q", null), 0, T0);
        t.update(update(null, "pytest -q", null, null, 3), T1);
        assertThat(t.updatedAt()).isEqualTo(T0);
    }

    // ---- retry ----

    @ParameterizedTest(name = "{0} 的任務可重試：retryCount+1 且回到 QUEUED")
    @EnumSource(value = TaskStatus.class, names = {"FAILED", "ESCALATED"})
    void retryIsAllowedOnlyFromFailedOrEscalated(TaskStatus from) {
        Task t = taskIn(from);
        t.retry(T1);
        assertThat(t.status()).isEqualTo(TaskStatus.QUEUED);
        assertThat(t.retryCount()).isEqualTo(2);
        assertThat(t.updatedAt()).isEqualTo(T1);
    }

    @ParameterizedTest(name = "{0} 的任務不可重試（409）")
    @EnumSource(value = TaskStatus.class, mode = EnumSource.Mode.EXCLUDE, names = {"FAILED", "ESCALATED"})
    void retryFromAnyOtherStatusIsConflictAndChangesNothing(TaskStatus from) {
        Task t = taskIn(from);
        // reason 必須是 retry 自己的規則（只允許 FAILED／ESCALATED），而不是狀態機的「非法狀態轉移」兜底——
        // 否則有人放寬這一關時，狀態機仍會擋下來，測試就看不出規則被改了。
        assertThatThrownBy(() -> t.retry(T1)).isInstanceOfSatisfying(ConflictException.class,
                e -> assertThat(e.reason()).isEqualTo("目前狀態不可重試"));
        assertThat(t.status()).isEqualTo(from);
        assertThat(t.retryCount()).isEqualTo(1);
    }

    // ---- 狀態機 ----

    @Test
    void transitionToFollowsAppendixB3() {
        Task t = taskIn(TaskStatus.PENDING);
        t.transitionTo(TaskStatus.QUEUED, T1);
        t.transitionTo(TaskStatus.RUNNING, T1);
        t.transitionTo(TaskStatus.VALIDATING, T1);
        t.transitionTo(TaskStatus.COMPLETED, T1);
        assertThat(t.status()).isEqualTo(TaskStatus.COMPLETED);
        assertThatThrownBy(() -> t.transitionTo(TaskStatus.QUEUED, T1))
                .isInstanceOf(IllegalStateTransitionException.class);
    }

    // ---- 刪除 ----

    @Test
    void runningTaskCannotBeDeleted() {
        Task t = taskIn(TaskStatus.RUNNING);
        assertThatThrownBy(() -> t.softDelete(T1)).isInstanceOf(ConflictException.class);
        assertThat(t.deleted()).isFalse();
    }

    @ParameterizedTest(name = "{0} 的任務可軟刪除")
    @EnumSource(value = TaskStatus.class, mode = EnumSource.Mode.EXCLUDE, names = {"RUNNING"})
    void anyNonRunningTaskCanBeSoftDeleted(TaskStatus from) {
        Task t = taskIn(from);
        t.softDelete(T1);
        assertThat(t.deleted()).isTrue();
        assertThat(t.status()).isEqualTo(from);
        assertThat(t.deletedAt()).as("V9：軟刪除記下刪除時間，復原與清除據此辨識").isEqualTo(T1);
    }

    // ---- signoff ----

    @Test
    void signoffRulesMatchTheProjectOnes() {
        Task t = Task.create(GOAL, new NewTask("t", null, "c", null, null, null, null, null, true), 0, T0);
        assertThatThrownBy(() -> t.signoff(null, T1)).isInstanceOf(ValidationException.class);
        t.signoff("Carol", T1);
        assertThat(t.signedOff()).isTrue();
        assertThat(t.signedOffBy()).isEqualTo("Carol");
        assertThatThrownBy(() -> t.signoff("Dave", T1)).isInstanceOf(ConflictException.class);
    }
}
