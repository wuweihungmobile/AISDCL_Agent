package com.aisdlc.console.infrastructure.logging;

import org.junit.jupiter.api.Test;
import org.springframework.boot.EnvironmentPostProcessor;
import org.springframework.boot.logging.LogFile;
import org.springframework.core.Ordered;
import org.springframework.core.env.MapPropertySource;
import org.springframework.core.env.StandardEnvironment;
import org.springframework.core.io.support.SpringFactoriesLoader;

import java.io.File;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 檔案日誌的環境設定（契約附錄 D.2；C-16）。為什麼重要：日誌檔是 Docker 全棧下「事後追查」的主要材料（與 Bridge 共用 {@code app_logs} 卷）——
 * 但它絕不能在沒設 {@code LOG_DIR} 的環境（本機開發、測試）偷偷開始寫檔；設了之後檔名、格式（JSON 行）與保留天數要符合契約，
 * 而部署者明確設定的 {@code logging.*} 永遠優先。端到端（真的起一個 Spring Boot、真的寫出檔案）見 {@link FileLoggingProcessTest}。
 */
class FileLoggingEnvironmentPostProcessorTest {

    private final FileLoggingEnvironmentPostProcessor processor = new FileLoggingEnvironmentPostProcessor();

    /** 只含給定屬性的環境（拿掉系統環境變數與系統屬性：開發機上碰巧有 LOG_DIR 不能影響結果）。 */
    private StandardEnvironment environment(Map<String, Object> properties) {
        StandardEnvironment env = new StandardEnvironment();
        env.getPropertySources().remove(StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME);
        env.getPropertySources().remove(StandardEnvironment.SYSTEM_PROPERTIES_PROPERTY_SOURCE_NAME);
        env.getPropertySources().addFirst(new MapPropertySource("test", properties));
        return env;
    }

    @Test
    void withoutLogDirNothingIsAddedAndSpringBootHasNoLogFile() {
        StandardEnvironment env = environment(Map.of());

        processor.postProcessEnvironment(env, null);

        assertThat(env.getPropertySources().contains(FileLoggingEnvironmentPostProcessor.PROPERTY_SOURCE_NAME)).isFalse();
        assertThat(LogFile.get(env)).as("沒設 LOG_DIR：不寫檔，行為與沒有這支處理器時相同").isNull();
        assertThat(env.getProperty("logging.structured.format.file")).isNull();
    }

    @Test
    void aBlankLogDirIsTreatedAsNotSet() {
        for (String blank : List.of("", "   ")) {
            StandardEnvironment env = environment(Map.of("LOG_DIR", blank));

            processor.postProcessEnvironment(env, null);

            assertThat(LogFile.get(env)).as("LOG_DIR='" + blank + "'").isNull();
        }
    }

    @Test
    void aLogDirTurnsOnAJsonLinesRollingFileNamedConsoleLogKeptForSevenDays() {
        StandardEnvironment env = environment(Map.of("LOG_DIR", "/app/logs"));

        processor.postProcessEnvironment(env, null);

        assertThat(LogFile.get(env)).isNotNull();
        assertThat(LogFile.get(env).toString()).isEqualTo(new File("/app/logs", "console.log").getPath());
        assertThat(env.getProperty("logging.structured.format.file")).isEqualTo("logstash");
        assertThat(env.getProperty("logging.logback.rollingpolicy.max-history", Integer.class)).isEqualTo(7);
    }

    @Test
    void whitespaceAroundTheDirectoryIsStripped() {
        StandardEnvironment env = environment(Map.of("LOG_DIR", "  /var/log/console  "));

        processor.postProcessEnvironment(env, null);

        assertThat(LogFile.get(env).toString()).isEqualTo(new File("/var/log/console", "console.log").getPath());
    }

    @Test
    void whatTheOperatorSetsExplicitlyAlwaysWinsOverTheDefaultsAddedHere() {
        StandardEnvironment env = environment(Map.of("LOG_DIR", "/app/logs", "logging.file.name", "/custom/my.log",
                "logging.structured.format.file", "ecs", "logging.logback.rollingpolicy.max-history", 30));

        processor.postProcessEnvironment(env, null);

        assertThat(LogFile.get(env).toString()).isEqualTo("/custom/my.log");
        assertThat(env.getProperty("logging.structured.format.file")).isEqualTo("ecs");
        assertThat(env.getProperty("logging.logback.rollingpolicy.max-history", Integer.class)).isEqualTo(30);
    }

    @Test
    void itRunsAfterTheConfigFilesAreLoadedSoExplicitSettingsInThemAreVisible() {
        assertThat(processor.getOrder()).isEqualTo(Ordered.LOWEST_PRECEDENCE);
    }

    @Test
    void springBootDiscoversItThroughMetaInfSpringFactories() {
        // Boot 自己的處理器（例如 CloudFoundry 那支）要建構子參數，這裡只關心我們的那一支，其餘的實例化失敗一律略過
        List<EnvironmentPostProcessor> registered = SpringFactoriesLoader
                .forDefaultResourceLocation(getClass().getClassLoader())
                .load(EnvironmentPostProcessor.class, SpringFactoriesLoader.FailureHandler.handleMessage(
                        (message, failure) -> { }));

        assertThat(registered).as("沒登記在 spring.factories＝Boot 永遠不會呼叫它，而且不會有任何錯誤訊息")
                .anyMatch(FileLoggingEnvironmentPostProcessor.class::isInstance);
    }
}
