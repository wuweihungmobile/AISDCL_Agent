package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.infrastructure.persistence.entity.AuditLogEntity;
import com.aisdlc.console.infrastructure.persistence.repository.AuditLogJpaRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Clock;
import java.util.UUID;

/**
 * 審計落庫（NFR-9.2-07；V6 {@code audit_log}）。<b>失敗絕不影響主請求</b>：任何例外都只記 WARN（資料庫暫時不可用時，
 * 結構化日誌行仍然在——落庫是第二份、不是唯一一份）。不記請求本文、不記 query string（避免 access_token 落庫）。
 *
 * <p>一律在<b>自己的新交易</b>裡寫（REQUIRES_NEW）：用例內的獨立事件（例如 {@code settings.reveal}）發生在唯讀交易中，
 * 若沿用外層交易，PostgreSQL 會拒絕 INSERT 而靜默丟掉審計列；也讓「外層交易回滾」不會帶走這筆留痕。
 * 提交本身也在 try 之內，所以連提交失敗都不會冒到主請求。
 */
@Component
public class AuditLogWriter {

    private static final Logger LOG = LoggerFactory.getLogger(AuditLogWriter.class);

    /** 一列審計紀錄（欄位對映 audit_log；長度在寫入時截斷到欄位上限）。 */
    public record Entry(String subject, String role, String method, String path, String entityType, String entityId,
                        int httpStatus, String traceId) {
    }

    private final AuditLogJpaRepository repository;
    private final Clock clock;
    private final TransactionTemplate ownTransaction;

    AuditLogWriter(AuditLogJpaRepository repository, Clock clock, PlatformTransactionManager transactionManager) {
        this.repository = repository;
        this.clock = clock;
        this.ownTransaction = new TransactionTemplate(transactionManager);
        this.ownTransaction.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
    }

    public void write(Entry entry) {
        try {
            AuditLogEntity row = new AuditLogEntity();
            row.id = UUID.randomUUID();
            row.occurredAt = clock.instant();
            row.subject = clip(entry.subject(), 100);
            row.role = clip(entry.role(), 20);
            row.method = clip(entry.method(), 10);
            row.path = clip(entry.path(), 500);
            row.entityType = clip(entry.entityType(), 50);
            row.entityId = clip(entry.entityId(), 100);
            row.httpStatus = entry.httpStatus();
            row.traceId = clip(entry.traceId(), 64);
            ownTransaction.executeWithoutResult(status -> repository.save(row));
        } catch (RuntimeException e) {
            LOG.warn("審計落庫失敗（不影響主請求）：{}", e.toString());
        }
    }

    private static String clip(String value, int max) {
        return value == null ? null : value.length() <= max ? value : value.substring(0, max);
    }
}
