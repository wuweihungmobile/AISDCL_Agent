package com.aisdlc.console.support;

import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

/**
 * 全部整合測試共用的單一 PostgreSQL 容器（pgvector/pgvector:pg18，與 AutoClaude、正式 compose 同映像）。
 *
 * <p>以 JVM 級單例啟動一次（Testcontainers 的 Ryuk 會在 JVM 結束時回收），避免每個 Spring 快取 context
 * 各起一個容器。Docker daemon 必須在線。
 */
public final class SharedPostgres {

    public static final String IMAGE = "pgvector/pgvector:pg18";

    public static final PostgreSQLContainer INSTANCE = new PostgreSQLContainer(
            DockerImageName.parse(IMAGE).asCompatibleSubstituteFor("postgres"))
            .withDatabaseName("aisdlc")
            .withUsername("aisdlc")
            .withPassword("aisdlc-test");

    static {
        INSTANCE.start();
    }

    private SharedPostgres() {
    }
}
