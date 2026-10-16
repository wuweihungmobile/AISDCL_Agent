package com.aisdlc.console.support;

import org.testcontainers.containers.GenericContainer;
import org.testcontainers.utility.DockerImageName;

/**
 * 需要真 Redis 的整合測試共用的單一容器（{@code redis:7-alpine}，與 docker-compose 的 Redis 同系列）。
 *
 * <p>與 {@link SharedPostgres} 同一個做法：JVM 級單例、第一次用到才啟動（類別載入時），Testcontainers 的 Ryuk 會在 JVM 結束時回收。
 * 只有 {@code RefreshRevocationRedisIT} 用它（refresh token 撤銷名單的 Redis 實作，契約 §1.9.2）；其他整合測試完全不碰 Redis。
 */
public final class SharedRedis {

    public static final String IMAGE = "redis:7-alpine";
    public static final int PORT = 6379;

    public static final GenericContainer<?> INSTANCE = new GenericContainer<>(DockerImageName.parse(IMAGE))
            .withExposedPorts(PORT);

    static {
        INSTANCE.start();
    }

    private SharedRedis() {
    }

    public static String host() {
        return INSTANCE.getHost();
    }

    public static int port() {
        return INSTANCE.getMappedPort(PORT);
    }
}
