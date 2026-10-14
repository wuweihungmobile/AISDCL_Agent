package com.aisdlc.console.domain.model.goal;

import java.util.List;
import java.util.UUID;

/**
 * 建立目標的輸入值。
 *
 * @param dependsOn 前置依賴目標 id（null 視為空）
 * @param draft     true＝草案：signedOff=false；預設 false＝手動建立 signedOff=true
 */
public record NewGoal(String name, String description, String passCriteria, List<UUID> dependsOn,
                      boolean draft) {
}
