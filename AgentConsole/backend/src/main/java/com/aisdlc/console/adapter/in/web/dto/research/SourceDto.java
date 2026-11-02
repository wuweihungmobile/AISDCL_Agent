package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.domain.model.research.ResearchViews.Fetch;
import com.aisdlc.console.domain.model.research.ResearchViews.Source;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;

/** 來源（契約 §1.3 {@code SourceDto}）加它的全部抓取紀錄；T3 來源只當搜尋線索（{@code clueOnly}）。 */
@Schema(name = "SourceDto", description = "研究來源（S-NNN）與其抓取紀錄")
public record SourceDto(
        @NotNull String sourceNo,
        @NotNull @Schema(description = "ACADEMIC｜INDUSTRY｜OSS｜COMMUNITY") String layer,
        @NotNull @Schema(description = "T1 一手｜T2 二手｜T3 線索") String tier,
        @NotNull @Schema(description = "V1 只見標題與網址｜V2 已開啟頁面｜V3 原文已落地並專項抽取") String verification,
        @NotNull @Schema(description = "URL｜DOI｜COMMIT") String anchorKind,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String url,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String doi,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String gitCommit,
        @NotNull String title,
        @NotNull String authorsOrg,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "YYYY-MM-DD；未見為 null") String publishedAt,
        @NotNull String sourceType,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "SPDX 識別碼；null 與 UNKNOWN 皆顯示未見") String licenseSpdx,
        @NotNull String licenseNote,
        @NotNull boolean clueOnly,
        @NotNull List<FetchDto> fetches) {

    /** 一次抓取（含失敗與被拒；{@code observedBy} 為 BRIDGE 或 AGENT_DECLARED）。 */
    @Schema(name = "SourceFetchDto")
    public record FetchDto(
            @NotNull String fetchNo,
            @NotNull String method,
            @NotNull @Schema(description = "BRIDGE｜AGENT_DECLARED") String observedBy,
            @NotNull @Schema(description = "解析不出 host 的被拒外呼記保留字 (unparsed)") String host,
            @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) Integer httpStatus,
            @NotNull String outcome,
            @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String rawSha256,
            @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, format = "int64") Long rawBytes,
            @NotNull String fetchedAt) {

        static FetchDto from(Fetch fetch) {
            return new FetchDto(fetch.fetchNo(), fetch.method(), fetch.observedBy(), fetch.host(), fetch.httpStatus(), fetch.outcome(),
                    fetch.rawSha256(), fetch.rawBytes(), Iso.of(fetch.fetchedAt()));
        }
    }

    public static SourceDto from(Source source) {
        return new SourceDto(source.sourceNo(), source.layer(), source.tier(), source.verification(), source.anchorKind(), source.url(),
                source.doi(), source.gitCommit(), source.title(), source.authorsOrg(), Iso.of(source.publishedAt()), source.sourceType(),
                source.licenseSpdx(), source.licenseNote(), source.clueOnly(), source.fetches().stream().map(FetchDto::from).toList());
    }
}
