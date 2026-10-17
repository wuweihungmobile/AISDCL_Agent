package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.execution.ExecutionWarning;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/**
 * execute 的 201 回應的警告項（契約 §1.10.6，D-115-06）。目前兩種 {@code code}：{@code sdd_governance_inactive}（範圍內至少有一個 SDD 來源任務、
 * 但本批次<b>沒有</b>啟用 SDD 治理；{@code cause} 見契約 §1.10.5）與 {@code sdd_frozen_digest_absent}（已啟用治理，但凍結時沒有記錄內容摘要，
 * Bridge 的 201 {@code warnings} 原樣轉入，沒有 {@code cause}）。
 */
@Schema(name = "ExecutionWarning", description = "execute 的 201 回應的警告項（v1.5，D-115-06）。sdd_governance_inactive：範圍內至少有一個 SDD 來源任務，"
        + "但本批次沒有啟用 SDD 治理（沒有預檢、沒有 FSM 同步、step_id 維持 G<g>-T<t>、事後也不會有追溯報告）；sdd_frozen_digest_absent："
        + "已啟用 SDD 治理，但凍結時沒有記錄內容摘要，放行但無法偵測凍結後改檔（Bridge 回的 201 warnings 原樣轉入）")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ExecutionWarningDto(
        @NotNull @Schema(description = "sdd_governance_inactive 或 sdd_frozen_digest_absent；日後新增的值前端要原樣顯示、不崩潰（所以文件上不是列舉）")
        String code,
        @Schema(description = "只有 sdd_governance_inactive 帶：不成立的資格（契約 §1.10.5 的順序）——not_bound、token_not_configured、"
                + "mixed_scope、spec_mismatch、duplicate_step_id；日後新增的值前端要原樣顯示（所以文件上不是列舉）")
        String cause,
        @NotNull @Schema(description = "給人看的中文說明") String detail) {

    public static ExecutionWarningDto from(ExecutionWarning warning) {
        return new ExecutionWarningDto(warning.code(), warning.cause(), warning.detail());
    }
}
