package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.infrastructure.security.AuditLoggingFilter;
import com.aisdlc.console.infrastructure.security.ConsoleAuthProperties;
import com.aisdlc.console.infrastructure.security.ConsoleCorsProperties;
import com.aisdlc.console.infrastructure.security.JwtAuthenticationFilter;
import com.aisdlc.console.infrastructure.security.JwtTokenService;
import com.aisdlc.console.infrastructure.security.RestSecurityHandlers;
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

import java.util.List;

/**
 * 安全設定（ADR-001 D4；Architecture §8）：無狀態 JWT、RBAC、CORS。
 *
 * <p>RBAC（NFR-9.2-02；Architecture §8.2）：
 * <ul>
 *   <li>免認證：登入／續期、{@code /actuator/health}、{@code /actuator/prometheus}（nginx 對外擋 /actuator/）、
 *       {@code /v3/api-docs}、{@code /swagger-ui}。</li>
 *   <li>{@code GET /api/v1/**}：VIEWER／OPERATOR／ADMIN。</li>
 *   <li>其餘 {@code /api/v1/**}（POST／PUT／DELETE）：OPERATOR／ADMIN（VIEWER 只能讀）。</li>
 *   <li>其餘 {@code /actuator/**}：僅 ADMIN。</li>
 * </ul>
 */
@Configuration
@EnableConfigurationProperties({ConsoleAuthProperties.class, ConsoleCorsProperties.class})
public class SecurityConfig {

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http, JwtTokenService jwt,
            @Qualifier("handlerExceptionResolver") HandlerExceptionResolver resolver) throws Exception {
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
                        .requestMatchers("/api/v1/**").hasAnyRole("OPERATOR", "ADMIN")
                        .requestMatchers("/actuator/**").hasRole("ADMIN")
                        .anyRequest().authenticated())
                .exceptionHandling(handling -> handling
                        .authenticationEntryPoint(RestSecurityHandlers.entryPoint(resolver))
                        .accessDeniedHandler(RestSecurityHandlers.accessDeniedHandler(resolver)))
                .addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class)
                .addFilterAfter(new AuditLoggingFilter(), JwtAuthenticationFilter.class);
        return http.build();
    }

    @Bean
    CorsConfigurationSource corsConfigurationSource(ConsoleCorsProperties properties) {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(properties.allowedOrigins());
        configuration.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(List.of("Authorization", "Content-Type", "Accept"));
        configuration.setExposedHeaders(List.of("X-Trace-Id"));
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
