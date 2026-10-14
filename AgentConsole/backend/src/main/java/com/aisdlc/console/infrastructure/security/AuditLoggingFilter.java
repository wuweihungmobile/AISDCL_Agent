package com.aisdlc.console.infrastructure.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * NFR-9.2-07 審計：每次寫入類請求（POST／PUT／PATCH／DELETE，限 /api/）結束後，輸出一行結構化 JSON 到
 * 名為 {@code audit} 的 logger：subject、method、path、targetId、status、traceId（Architecture §8.6）。
 *
 * <p>只記「誰、對什麼、結果如何」，不記請求本文（避免把密碼或敏感參數寫進日誌）。放在 JWT filter 之後、授權之前，
 * 因此被拒絕的寫入（401／403）同樣會留下審計紀錄。本 filter 不是 Spring Bean（理由同 JwtAuthenticationFilter）。
 */
public final class AuditLoggingFilter extends OncePerRequestFilter {

    private static final Logger AUDIT = LoggerFactory.getLogger("audit");
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Set<String> WRITE_METHODS = Set.of("POST", "PUT", "PATCH", "DELETE");
    private static final Pattern UUID_IN_PATH = Pattern.compile(
            "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}");

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !WRITE_METHODS.contains(request.getMethod()) || !request.getRequestURI().startsWith("/api/");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        String subject = authentication == null ? null : authentication.getName();
        try {
            chain.doFilter(request, response);
        } finally {
            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("event", "audit");
            entry.put("subject", subject);
            entry.put("method", request.getMethod());
            entry.put("path", request.getRequestURI());
            entry.put("targetId", firstUuid(request.getRequestURI()));
            entry.put("status", response.getStatus());
            entry.put("traceId", MDC.get("traceId"));
            AUDIT.info(JSON.writeValueAsString(entry));
        }
    }

    private static String firstUuid(String path) {
        Matcher matcher = UUID_IN_PATH.matcher(path);
        return matcher.find() ? matcher.group() : null;
    }
}
