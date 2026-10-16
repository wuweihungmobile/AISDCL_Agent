package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.application.port.out.RefreshTokenRevocations;
import com.aisdlc.console.infrastructure.security.InMemoryRefreshTokenRevocations;
import com.aisdlc.console.infrastructure.security.ResilientRefreshTokenRevocations;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.data.redis.core.StringRedisTemplate;

import java.time.Clock;
import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

/**
 * 撤銷名單的選用（契約 §1.9.2、附錄 D.2；D-19）：{@code console.security.refresh-revocation.store} 與 {@code spring.data.redis.host}
 * 決定用哪一個實作。為什麼重要：本機開發與 e2e 不起 Redis——沒設 host 就必須是純記憶體，而且<b>連試都不試</b>（否則每次登入都等一次連線逾時、
 * 日誌被連線錯誤灌爆）；設了 host 才走 Redis 優先、不在線降級；明確選 {@code redis} 卻沒有連線設定要在啟動時就失敗，而不是第一次登入才炸。
 */
class RefreshRevocationConfigTest {

    private final ApplicationContextRunner runner = new ApplicationContextRunner()
            .withUserConfiguration(RefreshRevocationConfig.class).withBean(Clock.class, Clock::systemUTC);

    @Test
    void withoutARedisHostTheStoreIsPureMemoryAndTheRedisTemplateIsNeverTouched() {
        StringRedisTemplate template = mock(StringRedisTemplate.class);

        runner.withBean(StringRedisTemplate.class, () -> template).run(context -> {
            RefreshTokenRevocations revocations = context.getBean(RefreshTokenRevocations.class);

            assertThat(revocations).isInstanceOf(InMemoryRefreshTokenRevocations.class);
            assertThat(revocations.tryRevoke("jti-1", Instant.now().plusSeconds(60))).isTrue();
            assertThat(revocations.tryRevoke("jti-1", Instant.now().plusSeconds(60))).isFalse();
            // 容器自己會對它管理的 bean 呼叫生命週期回呼（Aware／afterPropertiesSet），那不算「碰」；真的碰 Redis 一定經過 opsForValue()
            verify(template, never()).opsForValue();
        });
    }

    @Test
    void aRedisHostMakesRedisFirstWithTheMemoryFallback() {
        runner.withBean(StringRedisTemplate.class, () -> mock(StringRedisTemplate.class))
                .withPropertyValues("spring.data.redis.host=redis").run(context ->
                        assertThat(context.getBean(RefreshTokenRevocations.class))
                                .isInstanceOf(ResilientRefreshTokenRevocations.class));
    }

    @Test
    void storeMemoryWinsOverAConfiguredHost() {
        StringRedisTemplate template = mock(StringRedisTemplate.class);

        runner.withBean(StringRedisTemplate.class, () -> template).withPropertyValues("spring.data.redis.host=redis",
                "console.security.refresh-revocation.store=memory").run(context -> {
                    RefreshTokenRevocations revocations = context.getBean(RefreshTokenRevocations.class);

                    assertThat(revocations).isInstanceOf(InMemoryRefreshTokenRevocations.class);
                    assertThat(revocations.tryRevoke("jti-2", Instant.now().plusSeconds(60))).isTrue();
                    verify(template, never()).opsForValue();
                });
    }

    @Test
    void storeRedisIsRedisFirstEvenWithoutAnExplicitHost() {
        runner.withBean(StringRedisTemplate.class, () -> mock(StringRedisTemplate.class))
                .withPropertyValues("console.security.refresh-revocation.store=redis").run(context ->
                        assertThat(context.getBean(RefreshTokenRevocations.class))
                                .isInstanceOf(ResilientRefreshTokenRevocations.class));
    }

    @Test
    void redisWithoutAConnectionBeanFailsAtStartup() {
        runner.withPropertyValues("console.security.refresh-revocation.store=redis").run(context -> {
            assertThat(context).hasFailed();
            assertThat(context.getStartupFailure()).hasRootCauseInstanceOf(IllegalStateException.class)
                    .rootCause().hasMessageContaining("refresh-revocation.store=redis");
        });
    }

    @Test
    void anUnknownStoreValueFailsAtStartup() {
        runner.withPropertyValues("console.security.refresh-revocation.store=bogus").run(context ->
                assertThat(context).hasFailed());
    }
}
