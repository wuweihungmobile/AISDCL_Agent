package com.aisdlc.console.infrastructure.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
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
 * 名為 {@code audit} 的 logger：subject、method、path、targetId、status、traceId（Architecture §8.6），
 * 並落一列到 {@code console.audit_log}（V6；{@link AuditLogWriter}，失敗不影響主請求）。
 *
 * <p>Phase 3～6 追加兩個欄位（契約 §0.4 第 5 點）：{@code action}（例：{@code import.signoff}、{@code settings.update}）
 * 與 {@code entity}（{@code <type>:<id>}），由用例透過 {@link RequestAuditTrail} 標註；沒有標註的請求不帶這兩個欄位。
 * 少量非機密的補充欄位（例：test-connection 的 host 與結果）放在 {@code detail}。
 *
 * <p>只記「誰、對什麼、結果如何」，不記請求本文（避免把密碼或敏感參數寫進日誌）、不記 query string
 * （避免 {@code access_token} 落日誌或資料庫）。放在 JWT 與限流 filter 之後、授權之前，
 * 因此被拒絕的寫入（401／403／429）同樣會留下審計紀錄。本 filter 不是 Spring Bean（理由同 JwtAuthenticationFilter）。
 */
public final class AuditLoggingFilter extends OncePerRequestFilter {

    private static final Logger AUDIT = LoggerFactory.getLogger("audit");
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Set<String> WRITE_METHODS = Set.of("POST", "PUT", "PATCH", "DELETE");
    private static final Pattern UUID_IN_PATH = Pattern.compile(
            "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}");
    private static final String API_PREFIX = "/api/v1/";

    private final AuditLogWriter writer;

    public AuditLoggingFilter(AuditLogWriter writer) {
        this.writer = writer;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !WRITE_METHODS.contains(request.getMethod()) || !request.getRequestURI().startsWith("/api/");
    }

    @Override
    @SuppressWarnings("unchecked")
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        String subject = authentication == null ? null : authentication.getName();
        String role = roleOf(authentication);
        try {
            chain.doFilter(request, response);
        } finally {
            String path = request.getRequestURI();
            String action = (String) request.getAttribute(RequestAuditTrail.ATTR_ACTION);
            String taggedType = (String) request.getAttribute(RequestAuditTrail.ATTR_ENTITY_TYPE);
            String taggedId = (String) request.getAttribute(RequestAuditTrail.ATTR_ENTITY_ID);
            Map<String, Object> extra = (Map<String, Object>) request.getAttribute(RequestAuditTrail.ATTR_EXTRA);
            String entityType = taggedType != null ? taggedType : typeOfPath(path);
            String entityId = taggedId != null ? taggedId : firstUuid(path);

            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("event", "audit");
            entry.put("subject", subject);
            entry.put("method", request.getMethod());
            entry.put("path", path);
            entry.put("targetId", firstUuid(path));
            entry.put("status", response.getStatus());
            entry.put("traceId", MDC.get("traceId"));
            if (action != null) {
                entry.put("action", action);
                entry.put("entity", entityId == null ? entityType : entityType + ":" + entityId);
            }
            if (extra != null) {
                entry.put("detail", extra);
            }
            AUDIT.info(JSON.writeValueAsString(entry));

            writer.write(new AuditLogWriter.Entry(subject, role, request.getMethod(), path, entityType, entityId,
                    response.getStatus(), MDC.get("traceId")));
        }
    }

    /** {@code ROLE_ADMIN} → {@code ADMIN}；未認證為 null。 */
    static String roleOf(Authentication authentication) {
        if (authentication == null) {
            return null;
        }
        return authentication.getAuthorities().stream().map(GrantedAuthority::getAuthority)
                .filter(a -> a.startsWith("ROLE_")).map(a -> a.substring("ROLE_".length())).findFirst().orElse(null);
    }

    /** {@code /api/v1/<type>/…} 的第一段（例：projects、import、settings）；其他路徑為 null。 */
    private static String typeOfPath(String path) {
        if (!path.startsWith(API_PREFIX)) {
            return null;
        }
        String rest = path.substring(API_PREFIX.length());
        int slash = rest.indexOf('/');
        String type = slash < 0 ? rest : rest.substring(0, slash);
        return type.isEmpty() ? null : type;
    }

    private static String firstUuid(String path) {
        Matcher matcher = UUID_IN_PATH.matcher(path);
        return matcher.find() ? matcher.group() : null;
    }
}
