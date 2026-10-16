package com.aisdlc.console.application.port.out;

import java.time.Instant;

/**
 * refresh token 撤銷名單（契約 §1.9.2；D-19；ADR-001 D16、D23）。鍵是 token 的 {@code jti}（名單只存「已撤銷的 jti」，不存 token 本身）；
 * 項目只需要活到該 token 的 {@code exp}（過了 {@code exp} 的 token 本來就被拒，不必再記）。
 *
 * <p>實作（{@code infrastructure.security}）：Redis 優先；Redis 不在線（連線失敗、逾時、任何例外）時降級為單實例記憶體名單並記 WARN
 * （只在狀態轉換時記）。access token 無狀態，不在名單內。
 */
public interface RefreshTokenRevocations {

    /**
     * <b>原子地</b>撤銷 {@code tokenId}（Redis：{@code SET key 1 NX EX ttl}；記憶體：{@code putIfAbsent} 語意）。
     *
     * @param expiresAt 該 refresh token 的 {@code exp}；項目保留到它為止（至少 1 秒）
     * @return true＝這次呼叫讓它從有效變成已撤銷；false＝它早已被撤銷（登出過，或另一個併發的換新搶先）
     */
    boolean tryRevoke(String tokenId, Instant expiresAt);
}
