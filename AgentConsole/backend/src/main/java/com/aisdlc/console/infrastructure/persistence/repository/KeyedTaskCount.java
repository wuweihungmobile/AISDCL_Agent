package com.aisdlc.console.infrastructure.persistence.repository;

import java.util.UUID;

/** JPQL 建構式投影：某個鍵（專案或目標 id）底下的任務總數與已完成數。 */
public record KeyedTaskCount(UUID key, Long total, Long completed) {
}
