package com.aisdlc.console.support;

import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

/**
 * 整合測試共同基底：完整 Spring Boot context ＋ 真 PostgreSQL（Testcontainers）。
 * 全部子類別共用同一組設定（含 MockMvc），因此 Spring 只會建立一個 context、一個容器。
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
public abstract class AbstractIntegrationTest {

    @DynamicPropertySource
    static void datasource(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", SharedPostgres.INSTANCE::getJdbcUrl);
        registry.add("spring.datasource.username", SharedPostgres.INSTANCE::getUsername);
        registry.add("spring.datasource.password", SharedPostgres.INSTANCE::getPassword);
    }
}
