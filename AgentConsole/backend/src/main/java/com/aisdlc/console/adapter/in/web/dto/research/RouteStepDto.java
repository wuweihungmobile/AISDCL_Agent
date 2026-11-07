package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.domain.model.research.ResearchRouteViews.RouteStep;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/** 分流的一個步驟（契約 §1.3；{@code argvRedacted} 是去敏後的 argv——GitHub token 只經環境、不在 argv，也不在任何落地面）。 */
@Schema(name = "RouteStepDto", description = "分流步驟：步序、步驟名、狀態、去敏 argv、結束碼、stdout／stderr 尾端")
public record RouteStepDto(
        @NotNull int stepNo,
        @NotNull @Schema(description = "VALIDATE_TARGET｜GIT_SWITCH｜SCAFFOLD_FILES｜GIT_INIT｜GIT_COMMIT｜GH_REPO_CREATE｜PUBLISH_DOCS｜COPY_WORKSPACE｜REGISTER_STUB｜IMPL_KEY_INIT｜BASELINE_ADOPT") String step,
        @NotNull @Schema(description = "RUNNING｜OK｜FAILED｜SKIPPED｜COMPENSATED") String status,
        @NotNull String argvRedacted,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) Integer exitCode,
        @NotNull String stdoutTail,
        @NotNull String stderrTail,
        @NotNull String startedAt,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String finishedAt) {

    static RouteStepDto from(RouteStep s) {
        return new RouteStepDto(s.stepNo(), s.step(), s.status(), s.argvRedacted(), s.exitCode(), s.stdoutTail(), s.stderrTail(), Iso.of(s.startedAt()),
                Iso.of(s.finishedAt()));
    }
}
