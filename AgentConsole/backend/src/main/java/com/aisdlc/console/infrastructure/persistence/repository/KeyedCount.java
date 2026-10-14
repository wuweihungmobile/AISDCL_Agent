package com.aisdlc.console.infrastructure.persistence.repository;

import java.util.UUID;

/** JPQL 建構式投影：某個鍵（專案 id）底下的筆數。 */
public record KeyedCount(UUID key, Long count) {
}
