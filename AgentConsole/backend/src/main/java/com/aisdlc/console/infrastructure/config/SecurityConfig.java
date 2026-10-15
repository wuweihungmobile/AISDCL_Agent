package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.infrastructure.security.AuditLogWriter;
import com.aisdlc.console.infrastructure.security.AuditLoggingFilter;
import com.aisdlc.console.infrastructure.security.ConsoleAuthProperties;
import com.aisdlc.console.infrastructure.security.ConsoleCorsProperties;
import com.aisdlc.console.infrastructure.security.EncryptionProperties;
import com.aisdlc.console.infrastructure.security.JwtAuthenticationFilter;
import com.aisdlc.console.infrastructure.security.JwtTokenService;
import com.aisdlc.console.infrastructure.security.RateLimitFilter;
import com.aisdlc.console.infrastructure.security.RestSecurityHandlers;
import jakarta.servlet.Filter;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.servlet.HandlerExceptionResolver;

import java.time.Clock;
import java.time.Duration;
import java.util.List;

/**
 * 安全設定（ADR-001 D4；Architecture §8）：無狀態 JWT、RBAC、限流、CORS。
 *
 * <p>RBAC（NFR-9.2-02；Architecture §8.2；契約 §0.4）：
 * <ul>
 *   <li>免認證：登入／續期、{@code /actuator/health}、{@code /actuator/prometheus}（nginx 對外擋 /actuator/）、
 *       {@code /v3/api-docs}、{@code /swagger-ui}。</li>
 *   <li>{@code GET /api/v1/**}：VIEWER／OPERATOR／ADMIN。</li>
 *   <li>{@code /api/v1/settings/**} 的<b>非 GET</b>：僅 ADMIN（含 {@code POST /settings/export｜import｜test-connection}：
 *       它們是 POST，但屬 ADMIN 專用）；{@code GET …?reveal=true} 由 Controller 檢查角色。</li>
 *   <li>其餘 {@code /api/v1/**}（POST／PUT／DELETE）：OPERATOR／ADMIN（VIEWER 只能讀）。</li>
 *   <li>其餘 {@code /actuator/**}：僅 ADMIN。</li>
 * </ul>
 * Filter 順序：{@code TraceIdFilter}（最外層）→ {@code JwtAuthenticationFilter} → {@link RateLimitFilter}（限流在授權
 * 判定之前，超限者先得 429）→ {@link AuditLoggingFilter}（被授權層拒絕的寫入——401／403——同樣留審計）→ 授權。
 * 被限流的 429 請求不進審計：它們沒有執行任何寫入，而且逐筆落庫會讓限流本身變成「請求越多、寫庫越多」的放大器。
 */
@Configuration
@EnableConfigurationProperties({ConsoleAuthProperties.class, ConsoleCorsProperties.class, EncryptionProperties.class,
        ConsoleSecurityProperties.class})
public class SecurityConfig {

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http, JwtTokenService jwt,
            @Qualifier("handlerExceptionResolver") HandlerExceptionResolver resolver,
            ConsoleSecurityProperties security, AuditLogWriter auditWriter, Clock clock) throws Exception {
        JwtAuthenticationFilter jwtFilter = new JwtAuthenticationFilter(jwt);
        http
                .csrf(AbstractHttpConfigurer::disable)
                .cors(Customizer.withDefaults())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(authorize -> authorize
                        .requestMatchers(HttpMethod.POST, "/api/v1/auth/login", "/api/v1/auth/refresh").permitAll()
                        .requestMatchers("/actuator/health", "/actuator/health/**", "/actuator/prometheus").permitAll()
                        .requestMatchers("/v3/api-docs", "/v3/api-docs/**", "/swagger-ui.html", "/swagger-ui/**")
                        .permitAll()
                        .requestMatchers(HttpMethod.GET, "/api/v1/**").hasAnyRole("VIEWER", "OPERATOR", "ADMIN")
                        .requestMatchers("/api/v1/settings/**").hasRole("ADMIN")
                        .requestMatchers("/api/v1/**").hasAnyRole("OPERATOR", "ADMIN")
                        .requestMatchers("/actuator/**").hasRole("ADMIN")
                        .anyRequest().authenticated())
                .exceptionHandling(handling -> handling
                        .authenticationEntryPoint(RestSecurityHandlers.entryPoint(resolver))
                        .accessDeniedHandler(RestSecurityHandlers.accessDeniedHandler(resolver)))
                .addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class);
        Class<? extends Filter> auditAnchor = JwtAuthenticationFilter.class;
        if (security.rateLimit().enabled()) {
            http.addFilterAfter(RateLimitFilter.create(security.rateLimit().requestsPerMinute(),
                    Duration.ofSeconds(60), clock, resolver), JwtAuthenticationFilter.class);
            auditAnchor = RateLimitFilter.class;
        }
        http.addFilterAfter(new AuditLoggingFilter(auditWriter), auditAnchor);
        return http.build();
    }

    @Bean
    CorsConfigurationSource corsConfigurationSource(ConsoleCorsProperties properties) {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(properties.allowedOrigins());
        configuration.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        // Last-Event-ID：EventSource／fetch 串流重連時帶的最後事件 id（契約 §0.4 第 3 點；SSE 屬 W3-B2）
        configuration.setAllowedHeaders(List.of("Authorization", "Content-Type", "Accept", "Last-Event-ID"));
        // 讓瀏覽器端的 JS 讀得到：追蹤碼、新批次 id（審核 RETRY／SKIP）、限流的等待秒數、下載檔名
        configuration.setExposedHeaders(List.of("X-Trace-Id", "X-Follow-Up-Run-Id", "Retry-After",
                "Content-Disposition"));
        configuration.setMaxAge(3600L);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    /**
     * 使用者來自 application.yml 的 console.auth.users（由 AuthService 自行驗證），Spring Security 不需要
     * 自己的 UserDetailsService。明確宣告一個「永遠找不到使用者」的實作，讓 Boot 不要產生預設帳號與
     * 「Using generated security password」那一行日誌。
     */
    @Bean
    UserDetailsService noUserDetailsService() {
        return username -> {
            throw new UsernameNotFoundException("本系統不使用 Spring Security 的 UserDetailsService");
        };
    }
}
