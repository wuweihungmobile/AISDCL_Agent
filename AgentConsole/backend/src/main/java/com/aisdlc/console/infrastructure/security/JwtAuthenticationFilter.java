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
 * <p>token 無效或過期時「不」在這裡回應：只記下原因（request attribute），讓請求以匿名身分往下走，
 * 由 Spring Security 對受保護路徑回 401（{@link RestSecurityHandlers}），免認證路徑則不受影響。
 * 本 filter 只由 SecurityConfig 放進安全鏈，刻意不是 Spring Bean（否則會被 Boot 另外註冊成全域 servlet filter）。
 */
public final class JwtAuthenticationFilter extends OncePerRequestFilter {

    /** 失敗原因（TOKEN_EXPIRED／TOKEN_INVALID）的 request attribute 名稱。 */
    static final String AUTH_ERROR_ATTRIBUTE = "console.auth.error";
    private static final String BEARER = "Bearer ";

    private final JwtTokenService jwt;

    public JwtAuthenticationFilter(JwtTokenService jwt) {
        this.jwt = jwt;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String header = request.getHeader("Authorization");
        if (header != null && header.regionMatches(true, 0, BEARER, 0, BEARER.length())) {
            Verification result = jwt.verify(header.substring(BEARER.length()).trim(), JwtTokenService.USE_ACCESS);
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
}
