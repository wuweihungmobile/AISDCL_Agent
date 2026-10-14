package com.aisdlc.console.domain.model.goal;

import java.util.List;
import java.util.UUID;

/**
 * 更新目標的輸入值；所有欄位選填，null＝不變更。
 *
 * @param dependsOn null＝不變；空清單＝清除全部依賴；有值＝整組取代（成環／自依賴／跨專案由 application 層擋）
 */
public record GoalUpdate(String name, String description, String passCriteria, Integer sortOrder,
                         List<UUID> dependsOn) {
}
