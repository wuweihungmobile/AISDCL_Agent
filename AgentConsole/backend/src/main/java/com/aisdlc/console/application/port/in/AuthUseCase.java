package com.aisdlc.console.application.port.in;

/** 認證用例（ADR-001 D4）：以帳密換 JWT、以 refresh token 續期。 */
public interface AuthUseCase {

    /**
     * 簽發結果。
     *
     * @param expiresIn access token 有效秒數
     * @param role      角色名稱（ADMIN／OPERATOR／VIEWER）
     */
    record TokenPair(String accessToken, String refreshToken, long expiresIn, String role) {
    }

    /** 帳密正確則簽發；帳號不存在或密碼錯誤一律同一則訊息（401），不洩漏是哪一個錯。 */
    TokenPair login(String username, String password);

    /** 以有效的 refresh token 換新的一組 token（輪替）；無效或過期＝401。 */
    TokenPair refresh(String refreshToken);
}
