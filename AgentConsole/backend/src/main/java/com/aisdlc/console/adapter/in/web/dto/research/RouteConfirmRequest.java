package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.application.port.in.ResearchRouteUseCase.RouteInput;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 分流確認的請求本文（僅 ADMIN；契約 §1.2、API-RP-14）：欄位同預演（{@link RoutePreviewRequest}）加 {@code retry}。approver 一律取 JWT subject、GitHub token 取後端設定鍵
 * {@code research.github_token}——兩者都不在本文，多帶的鍵被忽略。
 */
@JsonIgnoreProperties(ignoreUnknown = true)
@Schema(name = "RouteConfirmRequest", description = "分流確認：欄位同預演，另有 retry（沿用最近一筆 FAILED 的分流續跑；輸入須與先前相同）")
public record RouteConfirmRequest(
        @Schema(description = "軌道：A 或 B", allowableValues = {"A", "B"}) String track,
        @Schema(description = "軌道 A：落點目標") String targetModule,
        @Schema(description = "軌道 A：分支名") String branchName,
        @Schema(description = "軌道 A：基底 ref") String baseRef,
        @Schema(description = "軌道 B：專案名（內環鍵）") String projectName,
        @Schema(description = "軌道 B：範本") String stackTemplate,
        @Schema(description = "軌道 B：遠端庫名") String repoName,
        @Schema(description = "軌道 B：遠端庫擁有者") String owner,
        @Schema(description = "軌道 B：遠端可見性", allowableValues = {"PUBLIC", "PRIVATE"}) String visibility,
        @Schema(description = "PUBLIC 時重述庫名確認") String confirmRepoName,
        @Schema(description = "軌道 B：是否建立 GitHub 遠端") Boolean createGithub,
        @Schema(description = "軌道 B：是否展開 CI workflow") Boolean ci,
        @Schema(description = "軌道 B：是否展開 docker-compose") Boolean dockerCompose,
        @Schema(description = "分流與 PRD target_scope 不同時必填，1～200 字") String scopeDiffersReason,
        @Schema(description = "重試最近一筆 FAILED 的分流（已完成的步驟不重做）") Boolean retry) {

    public RouteInput toInput() {
        return new RouteInput(track, targetModule, branchName, baseRef, projectName, stackTemplate, repoName, owner, visibility, confirmRepoName,
                createGithub, ci, dockerCompose, scopeDiffersReason, retry);
    }
}
