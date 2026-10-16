package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.application.port.out.RefreshTokenRevocations;
import com.aisdlc.console.infrastructure.config.ConsoleSecurityProperties.RefreshRevocation.Store;
import com.aisdlc.console.infrastructure.security.InMemoryRefreshTokenRevocations;
import com.aisdlc.console.infrastructure.security.RedisRefreshTokenRevocations;
import com.aisdlc.console.infrastructure.security.ResilientRefreshTokenRevocations;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.util.StringUtils;

import java.time.Clock;

/**
 * refresh token 撤銷名單的選用（契約 §1.9.2、附錄 D.2；D-19）。{@code console.security.refresh-revocation.store}：
 * <ul>
 *   <li>{@code auto}（預設）：{@code spring.data.redis.host} 有值才用 Redis（不在線時降級為記憶體並記 WARN），否則純記憶體——
 *       本機開發不必起 Redis，<b>也不會嘗試連線</b>（{@code SPRING_DATA_REDIS_HOST}／{@code _PORT} 是選填環境變數）；</li>
 *   <li>{@code redis}：只用 Redis（降級照舊）；</li>
 *   <li>{@code memory}：只用記憶體（本機 e2e、單元測試）。</li>
 * </ul>
 * 不使用 Redis 的情形下 {@link StringRedisTemplate} 根本不會被取用：Spring Boot 的 Lettuce 連線工廠是惰性連線，沒有人呼叫就不連。
 * 另須設 {@code management.health.redis.enabled=false}，否則 Redis 一掛 {@code /actuator/health} 變 DOWN、容器 unhealthy，
 * 降級承諾落空（application.yml）。
 */
@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(ConsoleSecurityProperties.class)
public class RefreshRevocationConfig {

    private static final Logger LOG = LoggerFactory.getLogger(RefreshRevocationConfig.class);

    @Bean
    RefreshTokenRevocations refreshTokenRevocations(ConsoleSecurityProperties security, Environment environment,
                                                    ObjectProvider<StringRedisTemplate> redis, Clock clock) {
        Store store = security.refreshRevocation().store();
        boolean hostConfigured = StringUtils.hasText(environment.getProperty("spring.data.redis.host"));
        InMemoryRefreshTokenRevocations memory = new InMemoryRefreshTokenRevocations(clock);
        boolean useRedis = switch (store) {
            case REDIS -> true;
            case MEMORY -> false;
            case AUTO -> hostConfigured;
        };
        if (!useRedis) {
            LOG.info("refresh token 撤銷名單：單實例記憶體（store={}，spring.data.redis.host {}）", store.name().toLowerCase(),
                    hostConfigured ? "已設定但 store=memory" : "未設定");
            return memory;
        }
        StringRedisTemplate template = redis.getIfAvailable();
        if (template == null) {
            throw new IllegalStateException("console.security.refresh-revocation.store=" + store.name().toLowerCase()
                    + " 但沒有 Redis 連線設定（spring.data.redis.*）");
        }
        LOG.info("refresh token 撤銷名單：Redis 優先（store={}；不在線時降級為單實例記憶體）", store.name().toLowerCase());
        return new ResilientRefreshTokenRevocations(new RedisRefreshTokenRevocations(template, clock), memory, clock);
    }
}
