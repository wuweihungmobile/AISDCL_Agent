package com.aisdlc.console.domain.model.config;

import java.time.Instant;
import java.util.UUID;

/**
 * 參數修改歷史的一列（PRD §5.5 US-S-07）。加密參數的 {@code oldValue}／{@code newValue} 一律是遮罩標記
 * （{@link #MASK}），絕不存明文或密文。
 *
 * @param id         新增時為 null（由持久層產生）
 * @param category   讀取時由 {@code system_configs} 帶出；新增時可為 null
 */
public record ConfigHistoryEntry(UUID id, UUID configId, String category, String key, String oldValue,
                                 String newValue, Instant changedAt, String changedBy) {

    /** 遮罩字串：U+2022 共八個（契約 §1.5）。 */
    public static final String MASK = "••••••••";
}
