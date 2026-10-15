package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ManageProjectUseCase.ProjectDetailView;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.GoalRepository;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.RuntimeSettings;
import com.aisdlc.console.application.port.out.TaskRepository;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

/**
 * 軟刪除專案的復原用例（契約 §1.6.1，C-3）。為什麼重要：整合測試只跑得到預設的 30 天；保留期是設定值，
 * 這裡釘住「視窗真的是設定的天數」（寫死 30 的實作在整合測試看不出來）、邊界剛好落在哪一側，以及被拒絕時什麼都沒動——
 * 復原失敗卻留下半套修改，比不能復原更糟。
 */
class ProjectServiceRestoreTest {

    private static final Instant NOW = Instant.parse("2026-10-16T08:00:00Z");

    private final ProjectRepository projects = mock(ProjectRepository.class);
    private final GoalRepository goals = mock(GoalRepository.class);
    private final TaskRepository tasks = mock(TaskRepository.class);
    private final RuntimeSettings settings = mock(RuntimeSettings.class);
    private final AuditTrail audit = mock(AuditTrail.class);
    private ProjectService service;

    @BeforeEach
    void setUp() {
        service = new ProjectService(projects, goals, tasks, settings, audit, Clock.fixed(NOW, ZoneOffset.UTC));
        when(settings.softDeleteRetentionDays()).thenReturn(30);
    }

    private Project deletedProject(Instant deletedAt) {
        Project project = Project.restore(UUID.randomUUID(), "已刪除的專案", "/work/deleted", "全部完成", null,
                ProjectStatus.ARCHIVED, 3, true, null, null, true, NOW.minus(Duration.ofDays(100)), deletedAt, "tester",
                deletedAt, ProjectStatus.READY);
        when(projects.findIncludingDeletedForUpdate(project.id())).thenReturn(Optional.of(project));
        when(projects.findById(project.id())).thenReturn(Optional.of(project));
        return project;
    }

    private void assertNothingWasTouched() {
        verify(projects, never()).save(any());
        verifyNoInteractions(goals);
        verifyNoInteractions(tasks);
        verifyNoInteractions(audit);
    }

    @ParameterizedTest(name = "保留期 {0} 天、{1} 小時前刪除 → 可復原＝{2}")
    @CsvSource({"7, 144, true", "7, 192, false", "90, 1080, true", "1, 25, false", "1, 23, true"})
    void theWindowIsTheConfiguredRetentionAndNotAHardCodedThirtyDays(int retentionDays, int hoursAgo,
                                                                       boolean restorable) {
        when(settings.softDeleteRetentionDays()).thenReturn(retentionDays);
        Project project = deletedProject(NOW.minus(Duration.ofHours(hoursAgo)));

        if (restorable) {
            assertThat(service.restore(project.id()).project().deleted()).isFalse();
        } else {
            assertThatThrownBy(() -> service.restore(project.id())).isInstanceOfSatisfying(ConflictException.class, e -> {
                assertThat(e.reason()).isEqualTo("restore_window_expired");
                assertThat(e.details()).containsEntry("retentionDays", retentionDays);
            });
            assertNothingWasTouched();
        }
    }

    @Test
    void exactlyAtTheCutoffIsStillRestorableAndOneMillisecondOlderIsNot() {
        Instant cutoff = NOW.minus(Duration.ofDays(30));
        Project atTheCutoff = deletedProject(cutoff);
        assertThat(service.restore(atTheCutoff.id()).project().deleted()).as("契約：deleted_at ≥ 現在 − 保留期").isFalse();

        Project tooOld = deletedProject(cutoff.minusMillis(1));
        assertThatThrownBy(() -> service.restore(tooOld.id())).isInstanceOfSatisfying(ConflictException.class,
                e -> assertThat(e.reason()).isEqualTo("restore_window_expired"));
    }

    @Test
    void aRestoreRecoversTheProjectThenBringsBackTheRowsDeletedAtTheSameInstantAndAuditsIt() {
        Instant deletedAt = NOW.minus(Duration.ofDays(3));
        Project project = deletedProject(deletedAt);

        ProjectDetailView view = service.restore(project.id());

        assertThat(view.project()).isSameAs(project);
        assertThat(project.deleted()).isFalse();
        assertThat(project.status()).as("還原為刪除前的狀態").isEqualTo(ProjectStatus.READY);
        assertThat(project.deletedAt()).isNull();
        assertThat(project.updatedAt()).isEqualTo(NOW);
        verify(projects).save(project);
        verify(goals).restoreDeletedWithProject(project.id(), deletedAt, NOW);
        verify(tasks).restoreDeletedWithProject(project.id(), deletedAt, NOW);
        verify(audit).note("project.restore", "project", project.id().toString());
    }

    @Test
    void aProjectThatIsNotDeletedIsRefusedWithItsStatusAndNothingIsTouched() {
        Project alive = Project.restore(UUID.randomUUID(), "存活", "/work/alive", "ok", null, ProjectStatus.READY, 3,
                true, null, null, false, NOW, NOW, "tester", null, null);
        when(projects.findIncludingDeletedForUpdate(alive.id())).thenReturn(Optional.of(alive));

        assertThatThrownBy(() -> service.restore(alive.id())).isInstanceOfSatisfying(ConflictException.class, e -> {
            assertThat(e.getMessage()).isEqualTo("專案未被刪除，不需復原");
            assertThat(e.reason()).isEqualTo("project_not_deleted");
            assertThat(e.details()).isEqualTo(Map.of("projectId", alive.id().toString(), "status", "READY"));
        });
        assertNothingWasTouched();
    }

    @Test
    void anUnknownProjectIsNotFoundWithTheDedicatedMessageAndNothingIsTouched() {
        UUID unknown = UUID.randomUUID();
        when(projects.findIncludingDeletedForUpdate(unknown)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.restore(unknown)).isInstanceOfSatisfying(NotFoundException.class,
                e -> assertThat(e.getMessage()).isEqualTo("專案不存在或已清除：" + unknown));
        assertNothingWasTouched();
    }
}
