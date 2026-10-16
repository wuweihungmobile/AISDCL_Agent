package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.signoff.PendingSignoffItem;
import com.aisdlc.console.domain.model.signoff.PendingSignoffKind;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.UUID;

/**
 * 待簽核草案清單的一筆（契約 §1.8.1；D-18）。{@code id} 也是對應 signoff 端點的路徑參數；<b>{@code IMPORT} 項的
 * {@code projectId}／{@code projectName}／{@code parentId} 為 null</b>（匯入記錄在 {@code confirm} 之前還沒有專案）。
 */
@Schema(name = "PendingSignoffItem", description = "待簽核草案清單的一筆（v1.4，D-18）。id 也是對應 signoff 端點的路徑參數"
        + "（/projects｜goals｜tasks/{id}/signoff、/import/{id}/signoff）。IMPORT 項的 projectId／projectName／parentId 為 null"
        + "（匯入記錄在 confirm 之前還沒有專案）")
public record PendingSignoffItemDto(
        @NotNull PendingSignoffKind kind,
        @NotNull UUID id,
        @NotNull @Schema(description = "所屬專案；PROJECT 項＝自己的 id；IMPORT 項為 null", nullable = true) UUID projectId,
        @NotNull @Schema(description = "所屬專案名稱；IMPORT 項為 null", nullable = true) String projectName,
        @NotNull @Schema(description = "PROJECT＝null；GOAL＝專案 id；TASK＝目標 id；IMPORT＝null", nullable = true) UUID parentId,
        @NotNull @Schema(description = "PROJECT／GOAL／TASK＝name；IMPORT＝source_file_name，沒有檔名（貼上文字）時為「貼上文字」") String title,
        @NotNull @Schema(description = "該列的 created_at（UTC）；清單依它升冪排序（同值以 id）") Instant createdAt) {

    public static PendingSignoffItemDto from(PendingSignoffItem item) {
        return new PendingSignoffItemDto(item.kind(), item.id(), item.projectId(), item.projectName(), item.parentId(),
                item.title(), item.createdAt());
    }
}
