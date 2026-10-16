package com.aisdlc.console.domain.model.signoff;

import java.time.Instant;
import java.util.UUID;

/**
 * 待簽核草案清單的一筆（契約 §1.8.1；D-18）。{@code id} 也是對應 signoff 端點的路徑參數
 * （{@code /projects｜goals｜tasks/{id}/signoff}、{@code /import/{id}/signoff}）。
 *
 * @param projectId   所屬專案；{@code PROJECT} 項＝自己的 id；<b>{@code IMPORT} 項為 null</b>（匯入記錄在 {@code confirm} 之前還沒有專案）
 * @param projectName 所屬專案名稱；{@code IMPORT} 項為 null
 * @param parentId    {@code PROJECT}＝null；{@code GOAL}＝專案 id；{@code TASK}＝目標 id；{@code IMPORT}＝null
 * @param title       {@code PROJECT}／{@code GOAL}／{@code TASK}＝{@code name}；{@code IMPORT}＝檔名，貼上文字沒有檔名時為「貼上文字」
 * @param createdAt   該列的 {@code created_at}；清單依它升冪排序（欄位可為 NULL，排最後）
 */
public record PendingSignoffItem(PendingSignoffKind kind, UUID id, UUID projectId, String projectName, UUID parentId,
                                 String title, Instant createdAt) {
}
