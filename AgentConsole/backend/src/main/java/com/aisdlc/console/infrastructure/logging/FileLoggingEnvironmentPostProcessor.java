package com.aisdlc.console.infrastructure.logging;

import org.springframework.boot.EnvironmentPostProcessor;
import org.springframework.boot.SpringApplication;
import org.springframework.core.Ordered;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.core.env.MapPropertySource;

import java.io.File;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 檔案日誌（契約附錄 D.2；C-16）：環境變數 {@code LOG_DIR} 有值時，console 照舊輸出，另把日誌以 <b>JSON 行</b>寫到
 * {@code ${LOG_DIR}/console.log}（每日切檔、保留 7 天）；沒設或空白時什麼都不改——行為與沒有這支類別時完全相同。
 * docker compose 對 backend 設 {@code LOG_DIR=/app/logs}（與 Bridge 共用 {@code app_logs} 卷）。
 *
 * <p><b>為什麼是 EnvironmentPostProcessor，不是 {@code logback-spring.xml}</b>：「有值才加 appender」在 Logback 1.5 只能用
 * {@code <if>}，那需要 Janino（本專案刻意不新增相依）；Spring Boot 的 {@code application.yml} 又算不出「{@code LOG_DIR} 有值才加上
 * {@code /console.log}」。所以這裡在 Environment 準備好、日誌系統初始化之前，條件式地補上 Boot 自己的檔案日誌屬性（Boot 的
 * Logback 設定據此建立 {@code RollingFileAppender}，JSON 由 {@code logging.structured.format.file=logstash} 產生，
 * MDC 的 {@code traceId} 會成為 JSON 欄位）。補的屬性放在<b>最低優先序</b>：部署者在 {@code application.yml}／環境變數明確設的
 * {@code logging.*} 一律優先。
 *
 * <p>寫不進去（目錄不可寫、卷唯讀）是 Logback appender 自己的啟動錯誤：記在日誌系統的狀態訊息，<b>不會讓服務起不來</b>。
 */
public final class FileLoggingEnvironmentPostProcessor implements EnvironmentPostProcessor, Ordered {

    /** 環境變數名稱（契約附錄 D.2）。 */
    static final String LOG_DIR_VARIABLE = "LOG_DIR";
    static final String FILE_NAME = "console.log";
    static final String PROPERTY_SOURCE_NAME = "consoleFileLogging";
    /** 保留幾天（每日切檔，保留 7 天）。 */
    static final int HISTORY_DAYS = 7;

    @Override
    public void postProcessEnvironment(ConfigurableEnvironment environment, SpringApplication application) {
        String dir = environment.getProperty(LOG_DIR_VARIABLE);
        if (dir == null || dir.isBlank()) {
            return;
        }
        Map<String, Object> defaults = new LinkedHashMap<>();
        defaults.put("logging.file.name", new File(dir.strip(), FILE_NAME).getPath());
        defaults.put("logging.structured.format.file", "logstash");
        defaults.put("logging.logback.rollingpolicy.max-history", HISTORY_DAYS);
        environment.getPropertySources().addLast(new MapPropertySource(PROPERTY_SOURCE_NAME, defaults));
    }

    /** 排在 Boot 載入 {@code application.yml} 的處理器之後（才看得到部署者在檔案裡明確設的 {@code logging.*}）。 */
    @Override
    public int getOrder() {
        return Ordered.LOWEST_PRECEDENCE;
    }
}
