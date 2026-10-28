package com.aisdlc.console.adapter.in.web.dto;

import com.fasterxml.jackson.annotation.JsonValue;
import io.swagger.v3.oas.annotations.media.Schema;

import java.util.Map;

/**
 * {@code GET /api/v1/sysadmin/backups} 的 {@code data}（TCS-SysAdminBackup-20261027 §C3.1；API-BK-01）：<b>保序 Map</b>——鍵序固定
 * （{@code control}、{@code timezone}、{@code activeJob}、{@code cards}、{@code backups}、{@code schedule}、{@code repos}、{@code walArchive}），
 * 缺鍵與 {@code null} 的語意不同（{@code null}＝該區塊因 {@code control.reason} 或來源失敗而不提供，<b>不得</b>以空陣列或 0 代替；非 ADMIN 的
 * {@code detailTail}、{@code requestedBy} 缺席）。所以不用具型別欄位（會把兩者都變成 null，也留不住「鍵缺席」）；欄位形狀見契約檔
 * {@code API_Contract_SysAdminBackup.md} 的 C3.1（先例 {@link IssueExportResponse}）。
 */
@Schema(name = "BackupOverviewResponse", type = "object", additionalProperties = Schema.AdditionalPropertiesValue.TRUE,
        description = "備份總覽（保序 Map，camelCase）。鍵序固定：control{available,canTrigger,reason,heartbeatAgeSeconds,exportAgeSeconds,"
                + "exportGeneratedAt,warnings[]}、timezone、activeJob、cards[4]（full、diff、dump、verify）、backups[]（新到舊）、schedule{entries[],retention}、"
                + "repos[]、walArchive{lastArchivedAt,failedCount,lastFailedAt}。control.reason 為 not_configured／schema_mismatch／export_unreadable 時，"
                + "其餘區塊全為 null（不是空陣列或 0）；runner_offline 時資料照回。非 ADMIN 沒有 detailTail、requestedBy。欄位形狀見契約檔 "
                + "API_Contract_SysAdminBackup.md 的 C3.1")
public final class BackupOverviewResponse {

    private final Map<String, Object> tree;

    private BackupOverviewResponse(Map<String, Object> tree) {
        this.tree = tree;
    }

    public static BackupOverviewResponse from(Map<String, Object> data) {
        return new BackupOverviewResponse(data);
    }

    /** 序列化的內容就是這棵樹本身（鍵序保留、{@code null} 照寫）。 */
    @JsonValue
    public Map<String, Object> tree() {
        return tree;
    }
}
