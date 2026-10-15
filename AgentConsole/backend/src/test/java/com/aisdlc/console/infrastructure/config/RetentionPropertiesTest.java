package com.aisdlc.console.infrastructure.config;

import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.ConfigDataApplicationContextInitializer;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Configuration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * 軟刪除保留設定（{@code console.retention.*}；契約 §1.6.5）。為什麼重要：保留期是「資料還救不救得回來」的唯一依據——
 * 預設要是 30 天（NFR-9.3-04）、清除排程預設要是<b>關</b>（實體刪除不可逆，必須由部署者明確開啟）；
 * 保留期 0 或負數會讓每一筆軟刪除立刻不可復原，那就不是軟刪除了，所以要在啟動時就擋下來並指名是哪個設定。
 */
class RetentionPropertiesTest {

    @Configuration
    @EnableConfigurationProperties(RetentionProperties.class)
    static class PropsConfig {
    }

    private final ApplicationContextRunner runner = new ApplicationContextRunner().withUserConfiguration(PropsConfig.class);

    @Test
    void theDefaultsAreThirtyDaysAndNoPurge() {
        runner.run(context -> {
            RetentionProperties props = context.getBean(RetentionProperties.class);
            assertThat(props.softDeleteDays()).isEqualTo(30);
            assertThat(props.purgeEnabled()).as("實體刪除不可逆：預設關閉").isFalse();
        });
    }

    @Test
    void bothValuesCanBeOverriddenAndOneDayIsTheSmallestAccepted() {
        runner.withPropertyValues("console.retention.soft-delete-days=1", "console.retention.purge-enabled=true")
                .run(context -> {
                    RetentionProperties props = context.getBean(RetentionProperties.class);
                    assertThat(props.softDeleteDays()).isEqualTo(1);
                    assertThat(props.purgeEnabled()).isTrue();
                });
        runner.withPropertyValues("console.retention.soft-delete-days=90")
                .run(context -> assertThat(context.getBean(RetentionProperties.class).softDeleteDays()).isEqualTo(90));
    }

    @Test
    void aRetentionBelowOneDayFailsStartupAndNamesTheProperty() {
        for (String days : new String[] {"0", "-5"}) {
            runner.withPropertyValues("console.retention.soft-delete-days=" + days).run(context -> {
                assertThat(context).hasFailed();
                assertThat(context.getStartupFailure()).hasStackTraceContaining("console.retention.soft-delete-days");
            });
        }
    }

    // ── application.yml 與文件載明的環境變數 ──────────────────────────────────────────

    private final ApplicationContextRunner withApplicationYml = new ApplicationContextRunner()
            .withInitializer(new ConfigDataApplicationContextInitializer()).withUserConfiguration(PropsConfig.class);

    @Test
    void theShippedApplicationYmlKeepsThirtyDaysAndNoPurge() {
        withApplicationYml.run(context -> {
            RetentionProperties props = context.getBean(RetentionProperties.class);
            assertThat(props.softDeleteDays()).isEqualTo(30);
            assertThat(props.purgeEnabled()).as("出貨設定預設關閉清除排程").isFalse();
        });
    }

    @Test
    void theDocumentedEnvironmentVariablesReachTheBoundProperties() {
        // Spring 的寬鬆綁定不會把 CONSOLE_RETENTION_SOFT_DELETE_DAYS 對到 soft-delete-days（環境變數的連字號要省略），
        // 所以 application.yml 以明確的佔位符承接；README 與 yml 註解寫的就是這兩個名字
        withApplicationYml.withSystemProperties("CONSOLE_RETENTION_SOFT_DELETE_DAYS=7",
                "CONSOLE_RETENTION_PURGE_ENABLED=true").run(context -> {
                    RetentionProperties props = context.getBean(RetentionProperties.class);
                    assertThat(props.softDeleteDays()).isEqualTo(7);
                    assertThat(props.purgeEnabled()).isTrue();
                });
    }

    @Test
    void aNonNumericRetentionInTheEnvironmentFailsStartupInsteadOfSilentlyFallingBack() {
        withApplicationYml.withSystemProperties("CONSOLE_RETENTION_SOFT_DELETE_DAYS=thirty")
                .run(context -> assertThat(context).hasFailed());
    }

    @Test
    void theConstructorRefusesAZeroRetentionDirectly() {
        assertThatThrownBy(() -> new RetentionProperties(0, false)).isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("≥ 1").hasMessageContaining("0");
    }
}
