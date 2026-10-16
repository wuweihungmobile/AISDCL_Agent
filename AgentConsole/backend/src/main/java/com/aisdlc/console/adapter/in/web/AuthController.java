package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.LoginRequest;
import com.aisdlc.console.adapter.in.web.dto.LogoutRequest;
import com.aisdlc.console.adapter.in.web.dto.RefreshRequest;
import com.aisdlc.console.adapter.in.web.dto.TokenResponse;
import com.aisdlc.console.application.port.in.AuthUseCase;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirements;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/** 認證端點（ADR-001 D4；免認證）：登入換 JWT、以 refresh token 續期、登出時撤銷 refresh token（v1.4，D-19）。 */
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
    @Operation(summary = "以 refresh token 換新的 token", description = "refresh token 無效、過期或已被撤銷回 401（reason INVALID_REFRESH_TOKEN）；"
            + "access token 不可當 refresh token 用。換新時原子地撤銷舊的 refresh token：同一個 token 的兩個併發換新只有一個成功（v1.4，D-19）")
    public ApiResult<TokenResponse> refresh(@Valid @RequestBody RefreshRequest request) {
        return ApiResult.ok(TokenResponse.from(auth.refresh(request.refreshToken())));
    }

    @PostMapping("/logout")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    @Operation(operationId = "logout", summary = "登出並撤銷 refresh token（v1.4 補充端點，D-19；免認證）",
            description = "登出時撤銷該 refresh token 的 jti（撤銷名單：Redis 優先，不在線降級為單實例記憶體並記 WARN；ADR-001 D16、D23）。"
                    + "免認證，與 login／refresh 同：登出時 access token 可能已過期，仍必須能撤銷 refresh token。"
                    + "請求格式合法就一律 204：refresh token 有效 → 撤銷；無效、過期、已被撤銷、或是 access token → 同樣 204、不撤銷任何東西"
                    + "（不讓這支端點變成探測 token 有效性的管道）。不撤銷 access token（無狀態，最長 30 分鐘後自然失效）。"
                    + "撤銷後再以該 refresh token 呼叫 POST /auth/refresh → 401 INVALID_REFRESH_TOKEN。")
    public void logout(@Valid @RequestBody LogoutRequest request) {
        auth.logout(request.refreshToken());
    }
}
