package com.aisdlc.console;

import com.aisdlc.console.support.SharedPostgres;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.postgresql.PostgreSQLContainer;

/** 讓 TestConsoleApplication（本機開發用）與測試共用同一個 pgvector/pgvector:pg18 容器。 */
@TestConfiguration(proxyBeanMethods = false)
class TestcontainersConfiguration {

    // destroyMethod="" ：容器是 JVM 級共用單例，不能隨某個 context 關閉而被 Spring 停掉。
    @Bean(destroyMethod = "")
    @ServiceConnection
    PostgreSQLContainer postgresContainer() {
        return SharedPostgres.INSTANCE;
    }

}
