package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.application.port.out.SiAuditRefSource;
import org.springframework.stereotype.Component;

import java.util.UUID;

/** {@link SiAuditRefSource} 的正式實作：每次一個新的隨機 UUID（{@link UUID#toString()} 恆為小寫正規形態）。 */
@Component
class RandomSiAuditRefSource implements SiAuditRefSource {

    @Override
    public String next() {
        return UUID.randomUUID().toString();
    }
}
