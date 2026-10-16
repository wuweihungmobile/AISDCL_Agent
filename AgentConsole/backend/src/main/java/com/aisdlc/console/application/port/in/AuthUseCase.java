package com.aisdlc.console.application.port.in;

/** 認證用例（ADR-001 D4）：以帳密換 JWT、以 refresh token 續期、登出時撤銷 refresh token。 */
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

    /**
     * 以有效的 refresh token 換新的一組 token（輪替）；無效、過期或<b>已被撤銷</b>＝401。換新時<b>原子地撤銷舊的 refresh token</b>
     * （契約 §1.9.2）：同一個 token 的兩個併發換新只有一個成功。
     */
    TokenPair refresh(String refreshToken);

    /**
     * 登出（契約 §1.9.1；D-19）：refresh token 有效 → 撤銷它的 {@code jti}；無效、過期、已被撤銷、或是 access token → <b>什麼都不做、也不丟例外</b>
     * （不讓這支端點變成探測 token 是否有效的管道）。不撤銷 access token（無狀態，最長 30 分鐘後自然失效）。
     */
    void logout(String refreshToken);
}
