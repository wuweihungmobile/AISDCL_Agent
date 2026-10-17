package com.aisdlc.minibridge;

import jakarta.servlet.Filter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.boot.autoconfigure.ImportAutoConfiguration;
import org.springframework.boot.http.converter.autoconfigure.HttpMessageConvertersAutoConfiguration;
import org.springframework.boot.jackson.autoconfigure.JacksonAutoConfiguration;
import org.springframework.boot.tomcat.autoconfigure.servlet.TomcatServletWebServerAutoConfiguration;
import org.springframework.boot.webmvc.autoconfigure.DispatcherServletAutoConfiguration;
import org.springframework.boot.webmvc.autoconfigure.WebMvcAutoConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.UUID;

/**
 * 迷你 Bridge 的 Spring Boot 應用：只裝配 Web（嵌入式 Tomcat、DispatcherServlet、MVC、Jackson 訊息轉換器），
 * 刻意<b>不</b>用 {@code @EnableAutoConfiguration}——classpath 上有 Security／JPA／Flyway／Actuator，全開會要求資料庫與認證。
 */
@Configuration(proxyBeanMethods = false)
@ImportAutoConfiguration({TomcatServletWebServerAutoConfiguration.class, DispatcherServletAutoConfiguration.class,
        WebMvcAutoConfiguration.class, HttpMessageConvertersAutoConfiguration.class, JacksonAutoConfiguration.class})
class MiniBridgeApp {

    static final String TRACE_HEADER = "X-Trace-Id";

    @Bean
    MiniBridgeController miniBridgeController(MiniBridge bridge) {
        return new MiniBridgeController(bridge);
    }

    /**
     * 對照真 Bridge 的 HTTP 中介層（契約 §3.1.1）：記下每個請求帶的 {@code X-Trace-Id}（供測試斷言「console-api 對 Bridge 的每個請求
     * 都帶標頭」），並<b>回應回帶同名標頭</b>（請求沒帶就自產一個 UUID）。
     */
    @Bean
    Filter miniBridgeTraceFilter(MiniBridge bridge) {
        return (request, response, chain) -> {
            HttpServletRequest http = (HttpServletRequest) request;
            String traceId = http.getHeader(TRACE_HEADER);
            bridge.recordTrace(http.getMethod() + " " + http.getRequestURI(), traceId);
            bridge.recordToken(http.getMethod() + " " + http.getRequestURI(), http.getHeader("X-Bridge-Token"));
            ((HttpServletResponse) response).setHeader(TRACE_HEADER,
                    traceId == null || traceId.isBlank() ? UUID.randomUUID().toString() : traceId);
            chain.doFilter(request, response);
        };
    }
}
