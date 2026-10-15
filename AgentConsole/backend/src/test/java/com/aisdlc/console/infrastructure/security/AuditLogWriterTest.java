package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.infrastructure.persistence.entity.AuditLogEntity;
import com.aisdlc.console.infrastructure.persistence.repository.AuditLogJpaRepository;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.TransactionStatus;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 審計落庫（NFR-9.2-07）。為什麼重要：審計是「事後追責」的唯一證據，但它絕不能反過來讓主請求失敗——
 * 資料庫暫時不可用、提交失敗、欄位超長都只能留下一行 WARN；它也必須在<b>自己的新交易</b>裡寫，
 * 否則用例內的唯讀交易（例如 {@code settings.reveal}）會讓 INSERT 被 PostgreSQL 拒絕、審計列靜默消失。
 */
class AuditLogWriterTest {

    private static final Clock CLOCK = Clock.fixed(Instant.parse("2026-10-15T08:00:00Z"), ZoneOffset.UTC);

    private final AuditLogJpaRepository repository = mock(AuditLogJpaRepository.class);
    private final PlatformTransactionManager transactions = mock(PlatformTransactionManager.class);
    private final AuditLogWriter writer = new AuditLogWriter(repository, CLOCK, transactions);

    private static AuditLogWriter.Entry entry(String subject, String path) {
        return new AuditLogWriter.Entry(subject, "ADMIN", "PUT", path, "settings", "agent.maxRetries", 200, "trace-1");
    }

    @Test
    void aRowIsSavedWithAllFieldsAndTheClocksTimestampInsideItsOwnNewTransaction() {
        TransactionStatus status = mock(TransactionStatus.class);
        when(transactions.getTransaction(any())).thenReturn(status);

        writer.write(entry("admin", "/api/v1/settings/agent/maxRetries"));

        ArgumentCaptor<TransactionDefinition> definition = ArgumentCaptor.forClass(TransactionDefinition.class);
        verify(transactions).getTransaction(definition.capture());
        assertThat(definition.getValue().getPropagationBehavior())
                .as("獨立交易：外層是唯讀交易時照樣寫得進去，外層回滾也帶不走審計列")
                .isEqualTo(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
        verify(transactions).commit(status);

        ArgumentCaptor<AuditLogEntity> saved = ArgumentCaptor.forClass(AuditLogEntity.class);
        verify(repository).save(saved.capture());
        AuditLogEntity row = saved.getValue();
        assertThat(row.id).isNotNull();
        assertThat(row.occurredAt).isEqualTo(Instant.parse("2026-10-15T08:00:00Z"));
        assertThat(row.subject).isEqualTo("admin");
        assertThat(row.role).isEqualTo("ADMIN");
        assertThat(row.method).isEqualTo("PUT");
        assertThat(row.path).isEqualTo("/api/v1/settings/agent/maxRetries");
        assertThat(row.entityType).isEqualTo("settings");
        assertThat(row.entityId).isEqualTo("agent.maxRetries");
        assertThat(row.httpStatus).isEqualTo(200);
        assertThat(row.traceId).isEqualTo("trace-1");
    }

    @Test
    void valuesLongerThanTheColumnsAreClippedInsteadOfFailingTheInsert() {
        writer.write(new AuditLogWriter.Entry("s".repeat(150), "R".repeat(30), "M".repeat(20), "/p".repeat(400),
                "t".repeat(80), "e".repeat(150), 500, "x".repeat(100)));

        ArgumentCaptor<AuditLogEntity> saved = ArgumentCaptor.forClass(AuditLogEntity.class);
        verify(repository).save(saved.capture());
        AuditLogEntity row = saved.getValue();
        assertThat(row.subject).hasSize(100);
        assertThat(row.role).hasSize(20);
        assertThat(row.method).hasSize(10);
        assertThat(row.path).hasSize(500);
        assertThat(row.entityType).hasSize(50);
        assertThat(row.entityId).hasSize(100);
        assertThat(row.traceId).hasSize(64);
    }

    @Test
    void anUnauthenticatedRequestIsRecordedWithNullSubjectAndRole() {
        writer.write(new AuditLogWriter.Entry(null, null, "POST", "/api/v1/projects", null, null, 401, null));

        ArgumentCaptor<AuditLogEntity> saved = ArgumentCaptor.forClass(AuditLogEntity.class);
        verify(repository).save(saved.capture());
        assertThat(saved.getValue().subject).isNull();
        assertThat(saved.getValue().role).isNull();
        assertThat(saved.getValue().httpStatus).isEqualTo(401);
    }

    @Test
    void aFailingInsertIsSwallowedSoTheMainRequestNeverNoticesAndTheTransactionIsRolledBack() {
        TransactionStatus status = mock(TransactionStatus.class);
        when(transactions.getTransaction(any())).thenReturn(status);
        doThrow(new IllegalStateException("db down")).when(repository).save(any());

        assertThatCode(() -> writer.write(entry("admin", "/api/v1/projects"))).doesNotThrowAnyException();
        verify(transactions).rollback(status);
    }

    @Test
    void aFailingCommitIsSwallowedToo() {
        TransactionStatus status = mock(TransactionStatus.class);
        when(transactions.getTransaction(any())).thenReturn(status);
        doThrow(new IllegalStateException("commit failed")).when(transactions).commit(status);

        assertThatCode(() -> writer.write(entry("admin", "/api/v1/projects"))).doesNotThrowAnyException();
    }

    @Test
    void aTransactionManagerThatCannotStartATransactionIsSwallowedToo() {
        when(transactions.getTransaction(any())).thenThrow(new IllegalStateException("no connection"));

        assertThatCode(() -> writer.write(entry("admin", "/api/v1/projects"))).doesNotThrowAnyException();
    }
}
