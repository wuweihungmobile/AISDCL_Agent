package com.aisdlc.console.infrastructure.persistence.repository;

import com.aisdlc.console.infrastructure.persistence.entity.ProjectEntity;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
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

    /**
     * SDD 綁定的持有者（契約 §1.10.5）：同 {@code execution_path}、以同一個 {@code sdd_project} 綁定、<b>未軟刪除</b>（{@code is_deleted}
     * 是可為 NULL 的布林，與 V12 部分唯一索引的 {@code IS NOT TRUE} 同義：NULL 也算未刪除）、且不是 {@code excluded} 的專案，依建立時間升冪。
     */
    @Query("select p.id from ProjectEntity p where p.executionPath = :path and p.sddProject = :key "
            + "and (p.deleted is null or p.deleted = false) and p.id <> :excluded order by p.createdAt, p.id")
    List<UUID> findSddBindingHolders(@Param("path") String path, @Param("key") String key,
                                     @Param("excluded") UUID excluded);
}
