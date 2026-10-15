package com.aisdlc.console.domain.model.config;

import java.math.BigDecimal;
import java.util.List;

/**
 * 設定鍵的程式內中繼資料（契約 §0.5：{@code options}／{@code min}／{@code max}／{@code effect} 放程式內，不入 DB；
 * 附錄 C 是唯一真相源）。{@code validation_rule}、{@code impact_note}、預設值與型別在資料庫（V5 寫入）。
 *
 * @param min     數值下限（含）；沒有則 null
 * @param max     數值上限（含）；沒有則 null
 * @param options ENUM 的可選值；其餘型別為空清單
 */
public record ConfigSpec(String category, String key, ConfigEffect effect, BigDecimal min, BigDecimal max,
                         List<String> options) {

    public String fullKey() {
        return category + "." + key;
    }
}
