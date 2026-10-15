package com.aisdlc.console.infrastructure.persistence.repository;

import com.aisdlc.console.infrastructure.persistence.entity.ImportRecordEntity;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;
import java.util.UUID;

public interface ImportRecordJpaRepository extends JpaRepository<ImportRecordEntity, UUID> {

    /** SELECT … FOR UPDATE：序列化同一筆匯入記錄的並發 parse／signoff／confirm。 */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select i from ImportRecordEntity i where i.id = :id")
    Optional<ImportRecordEntity> findForUpdate(@Param("id") UUID id);

    /** 啟動復原：殘留的 PARSING 一律退回 UPLOADED。 */
    @Modifying(flushAutomatically = true, clearAutomatically = true)
    @Query("update ImportRecordEntity i set i.status = 'UPLOADED' where i.status = 'PARSING'")
    int resetStaleParsing();
}
