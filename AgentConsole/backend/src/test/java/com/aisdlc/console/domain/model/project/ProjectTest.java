package com.aisdlc.console.domain.model.project;

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
import org.junit.jupiter.params.provider.NullSource;
import org.junit.jupiter.params.provider.ValueSource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ProjectTest {

    private static final Instant T0 = Instant.parse("2026-10-14T10:00:00Z");
    private static final Instant T1 = T0.plus(Duration.ofMinutes(5));

    private static NewProject spec() {
        return new NewProject("核心平台", "/work/core", "- 測試通過率 >= 95%", "## 說明", null, false);
    }

    private static Project projectIn(ProjectStatus status) {
        return Project.restore(UUID.randomUUID(), "核心平台", "/work/core", "標準", null, status, 3, true,
                null, null, false, T0, T0, "admin", null, null, null, null, null);
    }

    private static ProjectUpdate update(String name, String path, String criteria, String description,
                                        Integer autonomy, ProjectStatus status) {
        return new ProjectUpdate(name, path, criteria, description, autonomy, status);
    }

    // ---- 建立 ----

    @Test
    void manuallyCreatedProjectStartsAsDraftAlreadySignedOffWithDefaultAutonomy() {
        Project p = Project.create(spec(), "operator", T0);
        assertThat(p.id()).isNotNull();
        assertThat(p.status()).isEqualTo(ProjectStatus.DRAFT);
        assertThat(p.signedOff()).as("PRD §5.1.1：手動建立之專案預設 signedOff=true").isTrue();
        assertThat(p.signedOffBy()).isNull();
        assertThat(p.autonomyLevel()).isEqualTo(3);
        assertThat(p.createdBy()).isEqualTo("operator");
        assertThat(p.createdAt()).isEqualTo(T0).isEqualTo(p.updatedAt());
        assertThat(p.deleted()).isFalse();
    }

    @Test
    void draftFlagCreatesAnUnsignedProject() {
        Project p = Project.create(new NewProject("草案", "/work/x", "標準", null, 5, true), "operator", T0);
        assertThat(p.signedOff()).isFalse();
        assertThat(p.autonomyLevel()).isEqualTo(5);
    }

    @Test
    void nameIsTrimmedAndBlankDescriptionBecomesNull() {
        Project p = Project.create(new NewProject("  名稱  ", "/work/x", "標準", "   ", null, false), "u", T0);
        assertThat(p.name()).isEqualTo("名稱");
        assertThat(p.description()).isNull();
    }

    @Test
    void creationCollectsEveryViolationAtOnce() {
        assertThatThrownBy(() -> Project.create(new NewProject(" ", "relative/path", "", null, 11, false), "u", T0))
                .isInstanceOfSatisfying(ValidationException.class, e -> assertThat(e.violations())
                        .extracting("field")
                        .containsExactlyInAnyOrder("name", "executionPath", "passCriteria", "autonomyLevel"));
    }

    @ParameterizedTest(name = "接受的絕對路徑：{0}")
    @ValueSource(strings = {"/home/u/proj", "C:\\work\\proj", "D:/work/proj",
            "\\\\server\\share\\proj"})
    void absolutePathsInPosixWindowsAndUncStylesAreAccepted(String path) {
        Project p = Project.create(new NewProject("p", path, "標準", null, null, false), "u", T0);
        assertThat(p.executionPath()).isEqualTo(path);
    }

    @ParameterizedTest(name = "拒絕的路徑：{0}")
    @ValueSource(strings = {"relative/dir", "./here", "..\\up", "C:work", "~/home"})
    void relativePathsAreRejected(String path) {
        assertThatThrownBy(() -> Project.create(new NewProject("p", path, "標準", null, null, false), "u", T0))
                .isInstanceOfSatisfying(ValidationException.class,
                        e -> assertThat(e.violations().get(0).field()).isEqualTo("executionPath"));
    }

    @Test
    void autonomyBoundariesOneAndTenAreAcceptedZeroAndElevenAreNot() {
        assertThat(Project.create(new NewProject("p", "/x", "c", null, 1, false), "u", T0).autonomyLevel()).isEqualTo(1);
        assertThat(Project.create(new NewProject("p", "/x", "c", null, 10, false), "u", T0).autonomyLevel()).isEqualTo(10);
        assertThatThrownBy(() -> Project.create(new NewProject("p", "/x", "c", null, 0, false), "u", T0))
                .isInstanceOf(ValidationException.class);
        assertThatThrownBy(() -> Project.create(new NewProject("p", "/x", "c", null, 11, false), "u", T0))
                .isInstanceOf(ValidationException.class);
    }

    @Test
    void nameLongerThan200CharactersIsRejected() {
        assertThatThrownBy(() -> Project.create(new NewProject("x".repeat(201), "/x", "c", null, null, false), "u", T0))
                .isInstanceOfSatisfying(ValidationException.class,
                        e -> assertThat(e.violations().get(0).field()).isEqualTo("name"));
        assertThat(Project.create(new NewProject("x".repeat(200), "/x", "c", null, null, false), "u", T0).name())
                .hasSize(200);
    }

    // ---- 更新 ----

    @Test
    void updateAppliesOnlyProvidedFieldsAndBumpsUpdatedAtOnlyOnRealChange() {
        Project p = Project.create(spec(), "u", T0);
        p.update(update(null, null, null, null, null, null), T1);
        assertThat(p.updatedAt()).as("沒有任何變更不該動 updatedAt").isEqualTo(T0);

        p.update(update("新名稱", null, null, "", 7, null), T1);
        assertThat(p.name()).isEqualTo("新名稱");
        assertThat(p.description()).as("空白 description＝清除").isNull();
        assertThat(p.autonomyLevel()).isEqualTo(7);
        assertThat(p.executionPath()).isEqualTo("/work/core");
        assertThat(p.updatedAt()).isEqualTo(T1);
    }

    @Test
    void whileExecutingOnlyNameAndDescriptionMayChange() {
        Project p = projectIn(ProjectStatus.EXECUTING);
        p.update(update("改名", null, null, "新說明", null, null), T1);
        assertThat(p.name()).isEqualTo("改名");
        assertThat(p.description()).isEqualTo("新說明");
    }

    @Test
    void whileExecutingChangingOtherFieldsIsConflictWithReasonAndFieldList() {
        Project p = projectIn(ProjectStatus.EXECUTING);
        assertThatThrownBy(() -> p.update(update(null, "/other/path", "新標準", null, 9, ProjectStatus.READY), T1))
                .isInstanceOfSatisfying(ConflictException.class, e -> {
                    assertThat(e.reason()).contains("EXECUTING");
                    assertThat(e.details().get("fields"))
                            .isEqualTo(List.of("executionPath", "passCriteria", "autonomyLevel", "status"));
                });
        assertThat(p.executionPath()).as("409 不可留下半套修改").isEqualTo("/work/core");
    }

    @Test
    void whileExecutingResendingTheSameValuesIsNotAChange() {
        Project p = projectIn(ProjectStatus.EXECUTING);
        p.update(update("核心平台", "/work/core", "標準", null, 3, ProjectStatus.EXECUTING), T1);
        assertThat(p.status()).isEqualTo(ProjectStatus.EXECUTING);
    }

    @Test
    void manualStatusChangeFollowsTheStateMachine() {
        Project p = Project.create(spec(), "u", T0);
        p.update(update(null, null, null, null, null, ProjectStatus.READY), T1);
        assertThat(p.status()).isEqualTo(ProjectStatus.READY);
        assertThat(p.updatedAt()).isEqualTo(T1);
        p.update(update(null, null, null, null, null, ProjectStatus.DRAFT), T1);
        assertThat(p.status()).isEqualTo(ProjectStatus.DRAFT);
    }

    @Test
    void illegalStatusChangeLeavesTheOtherFieldsUntouched() {
        Project p = Project.create(spec(), "u", T0);
        assertThatThrownBy(() -> p.update(update("不該生效", null, null, null, null, ProjectStatus.COMPLETED), T1))
                .isInstanceOf(IllegalStateTransitionException.class);
        assertThat(p.name()).isEqualTo("核心平台");
        assertThat(p.status()).isEqualTo(ProjectStatus.DRAFT);
    }

    // ---- signoff ----

    @Test
    void signoffRecordsApproverAndTimeOnADraft() {
        Project p = Project.create(new NewProject("草案", "/x", "c", null, null, true), "u", T0);
        p.signoff("  Alice  ", T1);
        assertThat(p.signedOff()).isTrue();
        assertThat(p.signedOffBy()).isEqualTo("Alice");
        assertThat(p.signedOffAt()).isEqualTo(T1);
        assertThat(p.updatedAt()).isEqualTo(T1);
    }

    @ParameterizedTest(name = "不可匿名：approver=[{0}]")
    @NullSource
    @ValueSource(strings = {"", "   ", "\t"})
    void signoffWithoutApproverIsRejected(String approver) {
        Project p = Project.create(new NewProject("草案", "/x", "c", null, null, true), "u", T0);
        assertThatThrownBy(() -> p.signoff(approver, T1))
                .isInstanceOfSatisfying(ValidationException.class,
                        e -> assertThat(e.violations().get(0).field()).isEqualTo("approver"));
        assertThat(p.signedOff()).isFalse();
    }

    @Test
    void signoffTwiceIsConflictAndDoesNotOverwriteTheAuditTrail() {
        Project p = Project.create(new NewProject("草案", "/x", "c", null, null, true), "u", T0);
        p.signoff("Alice", T0);
        assertThatThrownBy(() -> p.signoff("Mallory", T1)).isInstanceOf(ConflictException.class);
        assertThat(p.signedOffBy()).isEqualTo("Alice");
    }

    // ---- 軟刪除 ----

    @ParameterizedTest(name = "{0} 的專案可軟刪除")
    @EnumSource(value = ProjectStatus.class, names = {"DRAFT", "READY", "COMPLETED", "FAILED"})
    void softDeleteArchivesAndMarksDeleted(ProjectStatus from) {
        Project p = projectIn(from);
        p.softDelete(T1);
        assertThat(p.status()).isEqualTo(ProjectStatus.ARCHIVED);
        assertThat(p.deleted()).isTrue();
        assertThat(p.updatedAt()).isEqualTo(T1);
    }

    @Test
    void executingProjectCannotBeDeleted() {
        Project p = projectIn(ProjectStatus.EXECUTING);
        assertThatThrownBy(() -> p.softDelete(T1)).isInstanceOf(ConflictException.class);
        assertThat(p.deleted()).isFalse();
        assertThat(p.status()).isEqualTo(ProjectStatus.EXECUTING);
        assertThat(p.deletedAt()).as("被擋下的刪除不留痕").isNull();
        assertThat(p.statusBeforeDelete()).isNull();
    }

    // ---- 軟刪除時間與復原（V9、C-3）----

    @ParameterizedTest(name = "{0} 的專案軟刪除時記下刪除時間與刪除前的狀態")
    @EnumSource(value = ProjectStatus.class, names = {"DRAFT", "READY", "COMPLETED", "FAILED"})
    void softDeleteRecordsTheDeletionTimeAndTheStatusItHadBefore(ProjectStatus from) {
        Project p = projectIn(from);

        p.softDelete(T1);

        assertThat(p.deletedAt()).isEqualTo(T1);
        assertThat(p.statusBeforeDelete()).as("軟刪除把 status 改成 ARCHIVED，復原才知道要回到哪").isEqualTo(from);
    }

    @ParameterizedTest(name = "{0} 的專案刪除後復原回到 {0}")
    @EnumSource(value = ProjectStatus.class, names = {"DRAFT", "READY", "COMPLETED", "FAILED"})
    void recoveringRestoresTheStatusBeforeTheDeletionAndClearsTheDeletionMarks(ProjectStatus from) {
        Project p = projectIn(from);
        p.softDelete(T1);
        Instant later = T1.plus(Duration.ofDays(3));

        p.recover(later);

        assertThat(p.status()).isEqualTo(from);
        assertThat(p.deleted()).isFalse();
        assertThat(p.deletedAt()).isNull();
        assertThat(p.statusBeforeDelete()).isNull();
        assertThat(p.updatedAt()).isEqualTo(later);
        assertThat(p.signedOff()).as("signoff 等其餘欄位原樣保留").isTrue();
    }

    @Test
    void aProjectDeletedBeforeV9HasNoRecordedStatusSoItComesBackAsDraftWhenUnsignedAndReadyWhenSigned() {
        Project unsigned = Project.restore(UUID.randomUUID(), "舊", "/x", "標準", null, ProjectStatus.ARCHIVED, 3, false,
                null, null, true, T0, T0, "admin", T0, null, null, null, null);
        Project signed = Project.restore(UUID.randomUUID(), "舊", "/x", "標準", null, ProjectStatus.ARCHIVED, 3, true,
                "boss", T0, true, T0, T0, "admin", T0, null, null, null, null);

        unsigned.recover(T1);
        signed.recover(T1);

        assertThat(unsigned.status()).isEqualTo(ProjectStatus.DRAFT);
        assertThat(signed.status()).isEqualTo(ProjectStatus.READY);
        assertThat(signed.signedOffBy()).isEqualTo("boss");
    }

    @Test
    void recoverIsASystemRestoreSoItIsNotBlockedByArchivedBeingTerminalInTheManualStateMachine() {
        Project p = projectIn(ProjectStatus.READY);
        p.softDelete(T1);
        assertThatThrownBy(() -> p.transitionTo(ProjectStatus.READY, T1)).as("手動 API 仍然遵守附錄 B：ARCHIVED 沒有出邊")
                .isInstanceOf(IllegalStateTransitionException.class);

        p.recover(T1);

        assertThat(p.status()).isEqualTo(ProjectStatus.READY);
    }

    // ---- SDD 綁定（V12；契約 §1.10.5）----

    @Test
    void aNewProjectHasNoBindingAndItsEffectiveFsmProjectIsItsName() {
        Project p = Project.create(spec(), "operator", T0);

        assertThat(p.sddProject()).isNull();
        assertThat(p.sddSpecDir()).isNull();
        assertThat(p.sddSpecFile()).isNull();
        assertThat(p.effectiveSddProject()).as("NULL＝用預設（專案名；Backend 不淨化）").isEqualTo("核心平台");
    }

    @Test
    void bindingGivenAtCreationIsKeptAndTheEffectiveValueIsTheStoredKey() {
        Project p = Project.create(new NewProject("核心平台", "/work/core", "標準", null, null, false, " e2e-alpha ",
                "/work/core/docs", "/work/core/docs/TCS-A.md"), "operator", T0);

        assertThat(p.sddProject()).isEqualTo("e2e-alpha");
        assertThat(p.sddSpecDir()).isEqualTo("/work/core/docs");
        assertThat(p.sddSpecFile()).isEqualTo("/work/core/docs/TCS-A.md");
        assertThat(p.effectiveSddProject()).isEqualTo("e2e-alpha");
    }

    @Test
    void rebindingReportsWhetherAnythingChangedAndOnlyThenTouchesUpdatedAt() {
        Project p = Project.create(spec(), "operator", T0);

        assertThat(p.rebindSddProject("alpha", T1)).isTrue();
        assertThat(p.updatedAt()).isEqualTo(T1);
        assertThat(p.rebindSddProject("alpha", T1.plusSeconds(60))).as("相同值＝冪等").isFalse();
        assertThat(p.updatedAt()).isEqualTo(T1);
        assertThat(p.rebindSddProject(null, T1.plusSeconds(120))).as("null＝清除，回到用預設").isTrue();
        assertThat(p.sddProject()).isNull();
        assertThat(p.effectiveSddProject()).isEqualTo("核心平台");
    }

    @ParameterizedTest(name = "FSM 專案不合法（第 {index} 組）")
    @ValueSource(strings = {"  ", "", "a\u0000b", "a\nb"})
    void blankOrControlCharacterBindingIsRejected(String bad) {
        Project p = Project.create(spec(), "operator", T0);

        assertThatThrownBy(() -> p.rebindSddProject(bad, T1)).isInstanceOf(ValidationException.class)
                .satisfies(e -> assertThat(((ValidationException) e).violations().get(0).field())
                        .isEqualTo("sddProject"));
    }

    @Test
    void anOverlongBindingIsRejectedAtTheColumnLimits() {
        Project p = Project.create(spec(), "operator", T0);

        assertThatThrownBy(() -> p.rebindSddProject("x".repeat(101), T1)).isInstanceOf(ValidationException.class);
        assertThat(p.rebindSddProject("x".repeat(100), T1)).isTrue();
        assertThatThrownBy(() -> p.bindSddSpec("/" + "d".repeat(500), null, T1))
                .isInstanceOf(ValidationException.class);
    }

    @Test
    void bindingTheSpecIsIdempotentAndLeavesUntouchedFieldsAlone() {
        Project p = Project.create(spec(), "operator", T0);

        assertThat(p.bindSddSpec("/work/core/docs", "/work/core/docs/TCS-A.md", T1)).isTrue();
        assertThat(p.bindSddSpec("/work/core/docs", "/work/core/docs/TCS-A.md", T1.plusSeconds(60)))
                .as("相同值＝冪等，不動 updatedAt").isFalse();
        assertThat(p.updatedAt()).isEqualTo(T1);
        assertThat(p.bindSddSpec(null, "/work/core/docs/TCS-B.md", T1.plusSeconds(120))).isTrue();
        assertThat(p.sddSpecDir()).as("null 的參數不動該欄位").isEqualTo("/work/core/docs");
        assertThat(p.sddSpecFile()).isEqualTo("/work/core/docs/TCS-B.md");
        assertThat(p.sddProject()).as("規格綁定不影響 FSM 專案鍵").isNull();
    }
}
