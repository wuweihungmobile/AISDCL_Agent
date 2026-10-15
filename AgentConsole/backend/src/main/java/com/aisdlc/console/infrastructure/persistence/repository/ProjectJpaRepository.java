package com.aisdlc.console.infrastructure.persistence.repository;

import com.aisdlc.console.infrastructure.persistence.entity.ProjectEntity;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;
import java.util.UUID;

public interface ProjectJpaRepository extends JpaRepository<ProjectEntity, UUID>,
        JpaSpecificationExecutor<ProjectEntity> {

    Optional<ProjectEntity> findByIdAndDeletedFalse(UUID id);

    /** SELECT … FOR UPDATE：序列化會改動整張專案圖的操作（目標依賴、重排）。 */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select p from ProjectEntity p where p.id = :id and p.deleted = false")
    Optional<ProjectEntity> findActiveByIdForUpdate(@Param("id") UUID id);

    /** 含已軟刪除者並鎖列（復原用，契約 §1.6.1）：序列化「復原」與「再次刪除」，也讓並發的兩個 restore 只有一個成功。 */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select p from ProjectEntity p where p.id = :id")
    Optional<ProjectEntity> findAnyByIdForUpdate(@Param("id") UUID id);
}
