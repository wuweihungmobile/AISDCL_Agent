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
import jakarta.servlet.DispatcherType;
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
 *   <li>免認證：登入／續期／登出、{@code /actuator/health}、{@code /actuator/prometheus}（nginx 對外擋 /actuator/）、
 *       {@code /v3/api-docs}、{@code /swagger-ui}。</li>
 *   <li>{@code GET /api/v1/**}：VIEWER／OPERATOR／ADMIN。</li>
 *   <li>{@code POST /api/v1/si/**}：僅 ADMIN（SelfImproving 寫入載體，TCS-SelfImprovingDecide-P2b W10；<b>置於通用 POST 規則之前</b>，
 *       否則 OPERATOR 會通過安全層）。帳號名單由用例入口另判（403 {@code si_write_forbidden}）。{@code /si/**} 的 PUT／PATCH／DELETE
 *       沒有對映：落在通用規則——VIEWER 403、OPERATOR／ADMIN 405。</li>
 *   <li>{@code PUT}、{@code DELETE /api/v1/issues/**}：僅 ADMIN（議題中心的優先順序，TCS-IssueCenter-20261027 R-IC-58；各一條規則，同樣<b>置於通用規則之前</b>）。</li>
 *   <li>{@code POST /api/v1/sysadmin/**}：僅 ADMIN（系統管理／資料庫備份的手動觸發，TCS-SysAdminBackup-20261027 R-BK-57；<b>置於通用規則之前</b>）。
 *       所有 GET 為 VIEWER 以上；{@code /sysadmin/**} 的 PUT、PATCH、DELETE 沒有對映（VIEWER 403、OPERATOR／ADMIN 404 或 405）。</li>
 *   <li>{@code POST /api/v1/research/projects/{id}/approve｜return｜route｜gates｜delivery/tag｜delivery/pr}、{@code POST /api/v1/research/allowlist}、
 *       {@code PATCH /api/v1/research/allowlist/{id}}、{@code POST /api/v1/research/watch-sources}、{@code PATCH /api/v1/research/watch-sources/{slug}}：
 *       僅 ADMIN（ResearchToPRD；各一條規則，<b>置於通用規則之前</b>；{@code route/preview} 是 OPERATOR；
 *       {@code reinit} 的換世代模式由 {@code ResearchCommandService} 另判，D-64）。所有研究 GET 與研究事件串流為 VIEWER 以上。</li>
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
                        // SseEmitter 完成時容器以 ASYNC dispatch 再走一次過濾鏈（契約 §2.1、TBC-1）：JwtAuthenticationFilter 是
                        // OncePerRequestFilter（不處理 ASYNC）、API 又沒有 session，這次 dispatch 會被判成未認證而在已提交的回應上丟
                        // AccessDeniedException。ASYNC dispatch 是同一個已授權請求的內部重派，放行它不開任何新入口。
                        .dispatcherTypeMatchers(DispatcherType.ASYNC).permitAll()
                        // 登出（v1.4，D-19）同樣免認證：登出時 access token 可能已過期，仍必須能撤銷 refresh token
                        .requestMatchers(HttpMethod.POST, "/api/v1/auth/login", "/api/v1/auth/refresh",
                                "/api/v1/auth/logout").permitAll()
                        .requestMatchers("/actuator/health", "/actuator/health/**", "/actuator/prometheus").permitAll()
                        .requestMatchers("/v3/api-docs", "/v3/api-docs/**", "/swagger-ui.html", "/swagger-ui/**")
                        .permitAll()
                        .requestMatchers(HttpMethod.GET, "/api/v1/**").hasAnyRole("VIEWER", "OPERATOR", "ADMIN")
                        // SelfImproving 寫入載體（P2b）：只有 ADMIN；必須在下面通用的 /api/v1/** 規則之前（先中者定案）
                        .requestMatchers(HttpMethod.POST, "/api/v1/si/**").hasRole("ADMIN")
                        // 議題中心的優先順序寫入（TCS-IssueCenter-20261027 R-IC-58）：PUT、DELETE 各一條，只有 ADMIN；同樣必須在通用規則之前，
                        // 否則 OPERATOR 會通過安全層
                        .requestMatchers(HttpMethod.PUT, "/api/v1/issues/**").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.DELETE, "/api/v1/issues/**").hasRole("ADMIN")
                        // 系統管理／資料庫備份的手動觸發（TCS-SysAdminBackup-20261027 R-BK-57）：POST 只有 ADMIN；同樣必須在通用規則之前，
                        // 否則 OPERATOR 會通過安全層。保留與排程沒有任何可寫面：PUT、PATCH、DELETE 沒有對映（落在通用規則）
                        .requestMatchers(HttpMethod.POST, "/api/v1/sysadmin/**").hasRole("ADMIN")
                        // 研究到規格的 ADMIN 專屬動作（TCS-ResearchToPRD-P0 §4 #16、AT-960-5-3；契約 API_Contract_ResearchToPRD §0.1、D-12）：每個精確路徑各一條規則，
                        // 同樣必須在通用規則之前（先中者定案），否則 OPERATOR 會通過安全層。{id} 位置以 * 比對單一路徑段；route/preview 不在此列（OPERATOR 可用）。
                        // 🔴 …/reinit 刻意不在此列：同一路徑的重試初始化模式為 OPERATOR 以上，matcher 無法依請求本文分流——換世代（generation:"next"）的角色檢查
                        // 在 ResearchCommandService（OPERATOR＝403 research_write_forbidden；VIEWER 由通用規則先擋＝403 ACCESS_DENIED；D-64、AT-960-15-9）
                        .requestMatchers(HttpMethod.POST, "/api/v1/research/projects/*/approve").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.POST, "/api/v1/research/projects/*/return").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.POST, "/api/v1/research/projects/*/route").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.POST, "/api/v1/research/projects/*/scr/*/apply").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.POST, "/api/v1/research/projects/*/gates").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.POST, "/api/v1/research/projects/*/delivery/tag").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.POST, "/api/v1/research/projects/*/delivery/pr").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.POST, "/api/v1/research/allowlist").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.PATCH, "/api/v1/research/allowlist/*").hasRole("ADMIN")
                        // 研究來源單一化（TCS-ResearchRegistry W-R5）：追蹤來源的新增與停用／啟用僅 ADMIN；同樣必須在通用規則之前。
                        // 登記同步（POST /api/v1/si/research-registry/sync）已由上方 /api/v1/si/** 的 ADMIN 規則涵蓋，不另開 matcher
                        .requestMatchers(HttpMethod.POST, "/api/v1/research/watch-sources").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.PATCH, "/api/v1/research/watch-sources/*").hasRole("ADMIN")
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
