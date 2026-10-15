package com.aisdlc.console.infrastructure.persistence.repository;

import com.aisdlc.console.infrastructure.persistence.entity.SystemConfigHistoryEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.UUID;

public interface SystemConfigHistoryJpaRepository extends JpaRepository<SystemConfigHistoryEntity, UUID> {
}
