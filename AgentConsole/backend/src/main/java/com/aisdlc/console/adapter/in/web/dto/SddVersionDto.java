package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.engine.SddVersion;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/** Bridge {@code GET /sdd/version} 的投影（契約 §1.7.1；D-16）。 */
@Schema(name = "SddVersion", description = "Bridge GET /sdd/version 的投影（v1.4，D-16）。root 是 Bridge 看到的目錄路徑"
        + "（Docker 下是容器內路徑；開發機上是主機絕對路徑），僅供顯示，前端預設只秀 latest")
public record SddVersionDto(
        @NotNull @Schema(description = "SDD 版本目錄名（例 AISDLC_SDD_v0.30）") String latest,
        @NotNull @Schema(description = "Bridge 端的目錄路徑（僅供顯示）") String root) {

    /** null（{@code GET /sdd/version} 失敗）→ null。 */
    public static SddVersionDto from(SddVersion version) {
        return version == null ? null : new SddVersionDto(version.latest(), version.root());
    }
}
