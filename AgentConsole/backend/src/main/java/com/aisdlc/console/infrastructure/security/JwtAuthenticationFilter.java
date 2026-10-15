package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.infrastructure.security.JwtTokenService.Outcome;
import com.aisdlc.console.infrastructure.security.JwtTokenService.Verification;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/**
 * 從 {@code Authorization: Bearer <access token>} 建立認證身分。
 *
 * <p>SSE 例外（契約 §2.1）：{@code GET /api/v1/stream/**} 另收 {@code ?access_token=<access token>}（EventSource 不能帶標頭）。
 * 標頭優先——帶了 Bearer 標頭就只看標頭（即使它無效也不退回 query）；其他路徑一律忽略這個 query 參數。
 * 只收 access token：refresh token 走同一個驗證（{@link JwtTokenService#USE_ACCESS}），一律 TOKEN_INVALID。
 *
 * <p>token 無效或過期時「不」在這裡回應：只記下原因（request attribute），讓請求以匿名身分往下走，
 * 由 Spring Security 對受保護路徑回 401（{@link RestSecurityHandlers}），免認證路徑則不受影響。
 * 本 filter 只由 SecurityConfig 放進安全鏈，刻意不是 Spring Bean（否則會被 Boot 另外註冊成全域 servlet filter）。
 */
public final class JwtAuthenticationFilter extends OncePerRequestFilter {

    /** 失敗原因（TOKEN_EXPIRED／TOKEN_INVALID）的 request attribute 名稱。 */
    static final String AUTH_ERROR_ATTRIBUTE = "console.auth.error";
    private static final String BEARER = "Bearer ";
    private static final String STREAM_PREFIX = "/api/v1/stream/";
    private static final String QUERY_TOKEN = "access_token";

    private final JwtTokenService jwt;

    public JwtAuthenticationFilter(JwtTokenService jwt) {
        this.jwt = jwt;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String token = tokenOf(request);
        if (token != null) {
            Verification result = jwt.verify(token, JwtTokenService.USE_ACCESS);
            if (result.outcome() == Outcome.VALID) {
                SecurityContext context = SecurityContextHolder.createEmptyContext();
                context.setAuthentication(UsernamePasswordAuthenticationToken.authenticated(result.username(), null,
                        List.of(new SimpleGrantedAuthority("ROLE_" + result.role().name()))));
                SecurityContextHolder.setContext(context);
            } else {
                request.setAttribute(AUTH_ERROR_ATTRIBUTE,
                        result.outcome() == Outcome.EXPIRED ? "TOKEN_EXPIRED" : "TOKEN_INVALID");
            }
        }
        chain.doFilter(request, response);
    }

    /** Bearer 標頭優先；沒有標頭時只有 SSE 路徑看 {@code access_token} 查詢參數；都沒有回 null。 */
    private static String tokenOf(HttpServletRequest request) {
        String header = request.getHeader("Authorization");
        if (header != null && header.regionMatches(true, 0, BEARER, 0, BEARER.length())) {
            return header.substring(BEARER.length()).trim();
        }
        if ("GET".equals(request.getMethod()) && request.getRequestURI().startsWith(STREAM_PREFIX)) {
            String fromQuery = request.getParameter(QUERY_TOKEN);
            return fromQuery == null || fromQuery.isBlank() ? null : fromQuery.trim();
        }
        return null;
    }
}
