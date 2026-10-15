package com.aisdlc.console.infrastructure.persistence.repository;

import com.aisdlc.console.infrastructure.persistence.entity.SystemConfigEntity;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface SystemConfigJpaRepository extends JpaRepository<SystemConfigEntity, UUID> {

    List<SystemConfigEntity> findByCategory(String category);

    Optional<SystemConfigEntity> findByCategoryAndConfigKey(String category, String configKey);

    /** SELECT … FOR UPDATE：token_guard 跨鍵校驗與寫入必須序列化。 */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select c from SystemConfigEntity c where c.category = :category and c.configKey = :key")
    Optional<SystemConfigEntity> findForUpdate(@Param("category") String category, @Param("key") String key);
}
