package com.aisdlc.console.infrastructure.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.MDC;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;

/**
 * 每個請求配一個新的 traceId（UUID）：寫進 MDC（日誌樣板的 {@code %X{traceId}}）與回應標頭 {@code X-Trace-Id}，
 * 並供統一回應封包取用（PRD §7.2；NFR-9.4-04「日誌含 traceId 串聯」）。
 *
 * <p>以最高優先序註冊成 servlet filter（WebConfig），早於 Spring Security，所以連 401／403 與 CORS 預檢也有 traceId。
 * 一律自己產生、不採用客戶端傳來的標頭，避免日誌注入。
 */
public final class TraceIdFilter extends OncePerRequestFilter {

    public static final String MDC_KEY = "traceId";
    public static final String HEADER = "X-Trace-Id";

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String traceId = UUID.randomUUID().toString();
        MDC.put(MDC_KEY, traceId);
        response.setHeader(HEADER, traceId);
        try {
            chain.doFilter(request, response);
        } finally {
            MDC.remove(MDC_KEY);
        }
    }
}
