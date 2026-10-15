package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.domain.exception.RateLimitedException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.servlet.HandlerExceptionResolver;

import java.io.IOException;
import java.time.Clock;
import java.time.Duration;

/**
 * 限流（NFR-9.2-06；契約 §0.4 第 4 點，AR-06）：{@code /api/**} 每個使用者每 60 秒 100 次。
 *
 * <ul>
 *   <li><b>鍵</b>＝已認證請求的 JWT subject；未認證（登入端點、無效 token 而回 401 的請求）才以客戶端 IP 為鍵。
 *       Docker 全棧下所有使用者都經 nginx，以連線位址為鍵會讓整個系統共用一個桶。IP 取
 *       {@code getRemoteAddr()}（docker／e2e 搭配 {@code server.forward-headers-strategy=native} 由 Tomcat 還原
 *       代理轉送的客戶端位址），<b>本類別絕不自行解析 X-Forwarded-For</b>（直連時偽造的標頭不會被採信）。</li>
 *   <li><b>位置</b>：{@code JwtAuthenticationFilter} 之後（才拿得到 subject）、授權判定之前——超限的請求先得 429，
 *       而不是 401／403。</li>
 *   <li>不計入：{@code /actuator/**}、{@code /v3/api-docs}、swagger（路徑不在 {@code /api/} 之下）。</li>
 *   <li>超限回 429（reason＝{@code 超過每分鐘 100 次請求上限}，details＝{@code {limit,windowSeconds,retryAfterSeconds}}）並帶
 *       {@code Retry-After}；成功回應帶 {@code X-RateLimit-Limit}／{@code X-RateLimit-Remaining}。錯誤封包由
 *       {@code GlobalExceptionHandler} 產生（整個後端唯一的錯誤格式產生處）。</li>
 * </ul>
 * 本 filter 不是 Spring Bean（理由同 JwtAuthenticationFilter：否則會被 Boot 另外註冊成全域 servlet filter）。
 */
public final class RateLimitFilter extends OncePerRequestFilter {

    private final RateLimiter limiter;
    private final HandlerExceptionResolver resolver;

    RateLimitFilter(RateLimiter limiter, HandlerExceptionResolver resolver) {
        this.limiter = limiter;
        this.resolver = resolver;
    }

    /** 由 SecurityConfig 組裝（{@link RateLimiter} 為套件私有，記憶體實作；Redis 為選配，行為在契約 §0.4 固定）。 */
    public static RateLimitFilter create(int requestsPerMinute, Duration window, Clock clock,
                                         HandlerExceptionResolver resolver) {
        return new RateLimitFilter(new RateLimiter(requestsPerMinute, window, clock), resolver);
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !request.getRequestURI().startsWith("/api/");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        RateLimiter.Decision decision = limiter.tryConsume(keyOf(request));
        response.setHeader("X-RateLimit-Limit", Integer.toString(limiter.limit()));
        response.setHeader("X-RateLimit-Remaining", Long.toString(decision.remaining()));
        if (!decision.allowed()) {
            response.setHeader("Retry-After", Long.toString(decision.retryAfterSeconds()));
            resolver.resolveException(request, response, null, new RateLimitedException(limiter.limit(),
                    (int) limiter.windowSeconds(), decision.retryAfterSeconds()));
            return;
        }
        chain.doFilter(request, response);
    }

    /** 已認證＝{@code u:<subject>}；未認證＝{@code ip:<客戶端位址>}（兩種鍵空間互不干擾）。 */
    static String keyOf(HttpServletRequest request) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.isAuthenticated() && authentication.getName() != null) {
            return "u:" + authentication.getName();
        }
        return "ip:" + request.getRemoteAddr();
    }
}
