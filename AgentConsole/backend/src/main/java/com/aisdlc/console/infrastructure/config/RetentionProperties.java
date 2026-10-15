package com.aisdlc.console.infrastructure.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

/**
 * 軟刪除資料的保留與清除（{@code console.retention.*}；契約 §1.6.5、附錄 D.2；ADR-001 D19；PRD NFR-9.3-04「所有刪除操作皆為
 * 軟刪除，支援 30 天內復原」）。
 *
 * @param softDeleteDays 軟刪除專案可復原的天數（≥ 1）；超過的專案不可經 API 復原（409 {@code restore_window_expired}），
 *                       與清除排程是否開啟無關
 * @param purgeEnabled   是否註冊每日清除排程；<b>預設關閉</b>——實體刪除不可逆，部署者必須明確開啟
 */
@ConfigurationProperties(prefix = "console.retention")
public record RetentionProperties(@DefaultValue("30") int softDeleteDays,
                                  @DefaultValue("false") boolean purgeEnabled) {

    public RetentionProperties {
        if (softDeleteDays < 1) {
            throw new IllegalArgumentException("console.retention.soft-delete-days 必須 ≥ 1（目前為 " + softDeleteDays
                    + "）：保留期 0 天等於軟刪除立即不可復原，那就不是軟刪除了");
        }
    }
}
