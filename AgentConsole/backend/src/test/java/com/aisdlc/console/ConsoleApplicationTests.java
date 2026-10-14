package com.aisdlc.console;

import com.aisdlc.console.support.AbstractIntegrationTest;
import org.junit.jupiter.api.Test;

/** 冒煙：完整 context（含 Flyway 遷移與 JPA schema validate）能在真 PostgreSQL 上啟動。 */
class ConsoleApplicationTests extends AbstractIntegrationTest {

    @Test
    void contextLoads() {
    }

}
