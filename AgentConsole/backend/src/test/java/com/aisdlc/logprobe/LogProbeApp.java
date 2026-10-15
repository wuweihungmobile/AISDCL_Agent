package com.aisdlc.logprobe;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.boot.Banner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.WebApplicationType;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.Configuration;

/**
 * 日誌設定的子行程探針：以<b>真實的</b> {@code application.yml} 與 {@code META-INF/spring.factories}（含檔案日誌的
 * EnvironmentPostProcessor）啟動一個沒有任何 Bean 的 Spring Boot 應用（不連資料庫、不開埠），記兩行日誌後結束。
 * 由 {@code FileLoggingProcessTest} 在獨立的 JVM 裡執行——日誌系統是整個 JVM 共用的，在測試 JVM 內重新初始化會污染其他測試
 * （迷你 Bridge 壓低 root 日誌等級就曾造成不相干測試變紅）。
 *
 * <p>放在 {@code com.aisdlc.logprobe}（不在 {@code com.aisdlc.console} 之下），不會被 Console 的元件掃描撈進去。
 */
public final class LogProbeApp {

    /** 記在 MDC 有 traceId 的那一行。 */
    public static final String LINE_WITH_TRACE = "probe-line-with-trace";
    /** 記在 MDC 沒有 traceId 的那一行。 */
    public static final String LINE_WITHOUT_TRACE = "probe-line-without-trace";
    public static final String TRACE_ID = "probe-trace-id";

    @Configuration(proxyBeanMethods = false)
    static class Empty {
    }

    private LogProbeApp() {
    }

    public static void main(String[] args) {
        SpringApplication app = new SpringApplication(Empty.class);
        app.setWebApplicationType(WebApplicationType.NONE);
        app.setBannerMode(Banner.Mode.OFF);
        try (ConfigurableApplicationContext ignored = app.run(args)) {
            Logger log = LoggerFactory.getLogger("probe");
            MDC.put("traceId", TRACE_ID);
            log.info(LINE_WITH_TRACE);
            MDC.remove("traceId");
            log.warn(LINE_WITHOUT_TRACE);
        }
    }
}
