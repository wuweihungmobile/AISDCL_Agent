package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.domain.model.auth.Role;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** 啟動期驗證：JWT_SECRET 缺或短於 32 字元＝啟動失敗（ADR-001 D4）。 */
class ConsoleAuthPropertiesTest {

    @Configuration
    @EnableConfigurationProperties(ConsoleAuthProperties.class)
    static class PropsConfig {
    }

    private final ApplicationContextRunner runner = new ApplicationContextRunner()
            .withUserConfiguration(PropsConfig.class)
            .withPropertyValues(
                    "console.auth.users[0].username=admin",
                    "console.auth.users[0].password-hash=$2a$10$placeholderplaceholderplaceholderplaceholderplaceh",
                    "console.auth.users[0].role=ADMIN");

    @Test
    void aMissingSecretFailsStartupAndNamesTheEnvironmentVariable() {
        runner.run(context -> {
            assertThat(context).hasFailed();
            assertThat(context.getStartupFailure()).hasStackTraceContaining("JWT_SECRET");
        });
    }

    @Test
    void aBlankSecretFailsStartup() {
        runner.withPropertyValues("console.auth.jwt-secret=").run(context -> assertThat(context).hasFailed());
    }

    @Test
    void aThirtyOneCharacterSecretFailsAndThirtyTwoPasses() {
        runner.withPropertyValues("console.auth.jwt-secret=" + "x".repeat(31)).run(context -> {
            assertThat(context).hasFailed();
            assertThat(context.getStartupFailure()).hasStackTraceContaining("32");
        });
        runner.withPropertyValues("console.auth.jwt-secret=" + "x".repeat(32))
                .run(context -> assertThat(context).hasNotFailed());
    }

    @Test
    void defaultsAreThirtyMinutesAndSevenDays() {
        runner.withPropertyValues("console.auth.jwt-secret=" + "s".repeat(40)).run(context -> {
            ConsoleAuthProperties props = context.getBean(ConsoleAuthProperties.class);
            assertThat(props.accessTokenTtl()).isEqualTo(Duration.ofMinutes(30));
            assertThat(props.refreshTokenTtl()).isEqualTo(Duration.ofDays(7));
            assertThat(props.users()).singleElement().satisfies(user -> {
                assertThat(user.username()).isEqualTo("admin");
                assertThat(user.role()).isEqualTo(Role.ADMIN);
            });
        });
    }

    @Test
    void atLeastOneUserIsRequired() {
        new ApplicationContextRunner().withUserConfiguration(PropsConfig.class)
                .withPropertyValues("console.auth.jwt-secret=" + "s".repeat(40))
                .run(context -> assertThat(context).hasFailed());
    }

    @Test
    void duplicateUsernamesAreRefused() {
        ConsoleAuthProperties props = new ConsoleAuthProperties("s".repeat(40), Duration.ofMinutes(30),
                Duration.ofDays(7), List.of(
                        new ConsoleAuthProperties.UserProperties("admin", "h1", Role.ADMIN),
                        new ConsoleAuthProperties.UserProperties("admin", "h2", Role.VIEWER)));
        assertThatThrownBy(() -> new ConfiguredUserDirectory(props)).isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("admin");
    }
}
