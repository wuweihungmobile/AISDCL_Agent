package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.domain.exception.ForbiddenException;
import com.aisdlc.console.domain.exception.UnauthorizedException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.web.servlet.HandlerExceptionResolver;

/**
 * 安全層的 401／403 處理：不自己拼 JSON，而是把例外轉成領域例外後交給 MVC 的
 * {@code HandlerExceptionResolver}，讓 GlobalExceptionHandler 以「同一個」PRD §7.2 錯誤封包回應
 * （含 traceId）——整個後端只有一個錯誤格式的產生處。
 */
public final class RestSecurityHandlers {

    private RestSecurityHandlers() {
    }

    /** 未認證（沒帶 token、token 無效或過期）→ 401。 */
    public static AuthenticationEntryPoint entryPoint(HandlerExceptionResolver resolver) {
        return (HttpServletRequest request, HttpServletResponse response, AuthenticationException ex) -> {
            Object failure = request.getAttribute(JwtAuthenticationFilter.AUTH_ERROR_ATTRIBUTE);
            String reason = failure == null ? "UNAUTHENTICATED" : failure.toString();
            String message = switch (reason) {
                case "TOKEN_EXPIRED" -> "access token 已過期，請使用 refresh token 續期";
                case "TOKEN_INVALID" -> "access token 無效";
                default -> "需要登入：請在 Authorization 標頭帶 Bearer access token";
            };
            resolver.resolveException(request, response, null, new UnauthorizedException(message, reason));
        };
    }

    /** 已認證但角色不足 → 403。 */
    public static AccessDeniedHandler accessDeniedHandler(HandlerExceptionResolver resolver) {
        return (HttpServletRequest request, HttpServletResponse response, AccessDeniedException ex) ->
                resolver.resolveException(request, response, null,
                        new ForbiddenException("權限不足：此操作需要更高的角色", "ACCESS_DENIED"));
    }
}
