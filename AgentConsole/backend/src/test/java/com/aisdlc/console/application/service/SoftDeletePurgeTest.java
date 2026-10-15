package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.ProjectPurger;
import com.aisdlc.console.application.port.out.RuntimeSettings;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.PlatformTransactionManager;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

/**
 * 軟刪除專案的清除排程（契約 §1.6.5，C-3）。為什麼重要：實體刪除不可逆——預設必須是「什麼都不註冊」，部署者明確開啟後才會動；
 * 開啟後的每一輪也不能因為一個壞專案或一次資料庫暫時失敗，就讓整個排程靜默死亡（{@code scheduleWithFixedDelay} 的任務一旦拋出例外，
 * 之後每一輪都被取消）或讓其他專案跟著不被清。
 */
class SoftDeletePurgeTest {

    private static final Instant NOW = Instant.parse("2026-10-16T08:00:00Z");

    private final RuntimeSettings settings = mock(RuntimeSettings.class);
    private final ProjectPurger purger = mock(ProjectPurger.class);
    private final AuditTrail audit = mock(AuditTrail.class);
    private final PlatformTransactionManager transactions = mock(PlatformTransactionManager.class);
    private SoftDeletePurge purge;

    @BeforeEach
    void setUp() {
        purge = new SoftDeletePurge(settings, purger, audit, Clock.fixed(NOW, ZoneOffset.UTC), transactions);
        when(settings.softDeleteRetentionDays()).thenReturn(30);
        when(settings.purgeEnabled()).thenReturn(false);
        when(purger.findExpired(any())).thenReturn(List.of());
        when(purger.purge(any())).thenReturn(true);
    }

    @AfterEach
    void stopTheScheduler() {
        purge.stop();
    }

    // ── 開關 ─────────────────────────────────────────────────────────────────────────

    @Test
    void whenPurgeIsNotEnabledNothingIsRegisteredAndNothingEverTouchesTheData() {
        assertThat(purge.start()).as("預設關閉：沒有註冊任何排程").isFalse();
        purge.onReady();

        assertThat(purge.isScheduled()).isFalse();
        verifyNoInteractions(purger);
        verifyNoInteractions(audit);
        verifyNoInteractions(transactions);
    }

    @Test
    void whenPurgeIsEnabledStartRegistersTheScheduleOnceAndStopCancelsIt() {
        when(settings.purgeEnabled()).thenReturn(true);

        assertThat(purge.start()).isTrue();
        assertThat(purge.isScheduled()).isTrue();
        assertThat(purge.start()).as("重複呼叫不會再註冊第二個排程").isTrue();
        assertThat(purge.isScheduled()).isTrue();
        verifyNoInteractions(purger);

        purge.stop();
        assertThat(purge.isScheduled()).isFalse();
        purge.stop();
        assertThat(purge.start()).as("停掉之後可以重新註冊").isTrue();
    }

    @Test
    void onReadyStartsTheScheduleWhenEnabled() {
        when(settings.purgeEnabled()).thenReturn(true);

        purge.onReady();

        assertThat(purge.isScheduled()).isTrue();
    }

    // ── 一輪清除 ─────────────────────────────────────────────────────────────────────

    @Test
    void theCutoffIsNowMinusTheRetentionAndMovesWithTheSetting() {
        purge.runOnce();
        verify(purger).findExpired(NOW.minus(Duration.ofDays(30)));

        when(settings.softDeleteRetentionDays()).thenReturn(7);
        purge.runOnce();
        verify(purger).findExpired(NOW.minus(Duration.ofDays(7)));
    }

    @Test
    void everyExpiredProjectIsPurgedInItsOwnTransactionAndAuditedAsTheSystem() {
        UUID a = UUID.randomUUID();
        UUID b = UUID.randomUUID();
        UUID c = UUID.randomUUID();
        when(purger.findExpired(any())).thenReturn(List.of(a, b, c));

        int purged = purge.runOnce();

        assertThat(purged).isEqualTo(3);
        verify(purger).purge(a);
        verify(purger).purge(b);
        verify(purger).purge(c);
        verify(transactions, times(3)).getTransaction(any());
        verify(transactions, times(3)).commit(any());
        verify(transactions, never()).rollback(any());
        for (UUID id : List.of(a, b, c)) {
            verify(audit).system("project.purge", "project", id.toString(), Map.of("retentionDays", 30));
        }
    }

    @Test
    void aProjectThatWasRestoredOrRemovedBetweenListingAndPurgingIsNeitherCountedNorAudited() {
        UUID gone = UUID.randomUUID();
        UUID kept = UUID.randomUUID();
        when(purger.findExpired(any())).thenReturn(List.of(gone, kept));
        when(purger.purge(gone)).thenReturn(false);

        int purged = purge.runOnce();

        assertThat(purged).isEqualTo(1);
        verify(audit, never()).system(any(), any(), eq(gone.toString()), any());
        verify(audit).system("project.purge", "project", kept.toString(), Map.of("retentionDays", 30));
    }

    @Test
    void oneFailingProjectIsRolledBackAndDoesNotStopTheOthers() {
        UUID first = UUID.randomUUID();
        UUID broken = UUID.randomUUID();
        UUID last = UUID.randomUUID();
        when(purger.findExpired(any())).thenReturn(List.of(first, broken, last));
        doThrow(new IllegalStateException("fk violation")).when(purger).purge(broken);

        int purged = purge.runOnce();

        assertThat(purged).as("壞掉的那個不算，其餘照清").isEqualTo(2);
        verify(transactions).rollback(any());
        verify(transactions, times(2)).commit(any());
        verify(audit).system("project.purge", "project", first.toString(), Map.of("retentionDays", 30));
        verify(audit).system("project.purge", "project", last.toString(), Map.of("retentionDays", 30));
        verify(audit, never()).system(any(), any(), eq(broken.toString()), any());
    }

    @Test
    void aRoundWithNothingExpiredTouchesNothing() {
        assertThat(purge.runOnce()).isZero();

        verify(purger, never()).purge(any());
        verifyNoInteractions(audit);
        verifyNoInteractions(transactions);
    }

    // ── 排程進入點 ───────────────────────────────────────────────────────────────────

    @Test
    void theScheduledEntryPointRunsARoundAndNeverLetsAnExceptionEscape() {
        UUID id = UUID.randomUUID();
        when(purger.findExpired(any())).thenReturn(List.of(id));
        purge.runOnceQuietly();
        verify(purger).purge(id);

        when(purger.findExpired(any())).thenThrow(new IllegalStateException("db down"));
        assertThatCode(purge::runOnceQuietly)
                .as("例外外洩會讓 scheduleWithFixedDelay 取消之後所有輪次，排程靜默死亡").doesNotThrowAnyException();
    }
}
