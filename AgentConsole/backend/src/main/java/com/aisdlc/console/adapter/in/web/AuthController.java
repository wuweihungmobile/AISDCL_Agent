package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.LoginRequest;
import com.aisdlc.console.adapter.in.web.dto.RefreshRequest;
import com.aisdlc.console.adapter.in.web.dto.TokenResponse;
import com.aisdlc.console.application.port.in.AuthUseCase;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirements;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** 認證端點（ADR-001 D4；免認證）：登入換 JWT、以 refresh token 續期。 */
@RestController
@RequestMapping("/api/v1/auth")
@Tag(name = "認證")
@SecurityRequirements
public class AuthController {

    private final AuthUseCase auth;

    public AuthController(AuthUseCase auth) {
        this.auth = auth;
    }

    @PostMapping("/login")
    @Operation(summary = "登入", description = "帳密正確回 accessToken（30 分鐘）與 refreshToken（7 天）；失敗一律 401")
    public ApiResult<TokenResponse> login(@Valid @RequestBody LoginRequest request) {
        return ApiResult.ok(TokenResponse.from(auth.login(request.username(), request.password())));
    }

    @PostMapping("/refresh")
    @Operation(summary = "以 refresh token 換新的 token", description = "refresh token 無效或過期回 401；access token 不可當 refresh token 用")
    public ApiResult<TokenResponse> refresh(@Valid @RequestBody RefreshRequest request) {
        return ApiResult.ok(TokenResponse.from(auth.refresh(request.refreshToken())));
    }
}
