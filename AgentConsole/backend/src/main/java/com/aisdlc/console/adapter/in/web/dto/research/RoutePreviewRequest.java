package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.application.port.in.ResearchRouteUseCase.RouteInput;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 分流預演的請求本文（契約 §1.2；D-106）：欄位全部選填（缺的由 Bridge 補預設；必填性依軌道由輸入閘與 Bridge 判）。<b>沒有</b> {@code targetPath}（已退役：路徑由 Bridge 導出）、
 * {@code approver}、{@code githubToken}——本文多帶的鍵被忽略。
 */
@JsonIgnoreProperties(ignoreUnknown = true)
@Schema(name = "RoutePreviewRequest", description = "分流預演：軌道 A（targetModule、branchName、baseRef）或軌道 B（projectName、stackTemplate、repoName、owner、visibility、createGithub、ci、dockerCompose）；"
        + "分流與 PRD target_scope 不同時須附 scopeDiffersReason（1～200 字）")
public record RoutePreviewRequest(
        @Schema(description = "軌道：A（併入既有模組的 feature 分支）或 B（獨立新專案）", allowableValues = {"A", "B"}) String track,
        @Schema(description = "軌道 A：落點目標（autoclaude｜agentconsole｜sdd｜monorepo）") String targetModule,
        @Schema(description = "軌道 A：分支名，^feature/[a-z0-9-]{1,40}$；缺＝feature/issue-<NNNN>") String branchName,
        @Schema(description = "軌道 A：基底 ref；缺＝main") String baseRef,
        @Schema(description = "軌道 B：專案名（內環鍵），^[a-z][a-z0-9-]{1,61}$") String projectName,
        @Schema(description = "軌道 B：範本（P1 僅 python-fastapi）") String stackTemplate,
        @Schema(description = "軌道 B：遠端庫名，^[a-z][a-z0-9-]{1,38}$；缺＝projectName") String repoName,
        @Schema(description = "軌道 B：遠端庫擁有者（GitHub 帳號或組織）") String owner,
        @Schema(description = "軌道 B：遠端可見性（預設 PRIVATE）", allowableValues = {"PUBLIC", "PRIVATE"}) String visibility,
        @Schema(description = "visibility=PUBLIC 時須重述庫名確認") String confirmRepoName,
        @Schema(description = "軌道 B：是否建立 GitHub 遠端（預設 false；true 時由後端設定的 token 經 Bridge 子行程環境傳給 gh）") Boolean createGithub,
        @Schema(description = "軌道 B：是否展開 CI workflow（預設 true）") Boolean ci,
        @Schema(description = "軌道 B：是否展開 docker-compose（預設 true）") Boolean dockerCompose,
        @Schema(description = "分流與 PRD target_scope 不同時必填，1～200 字") String scopeDiffersReason) {

    public RouteInput toInput() {
        return new RouteInput(track, targetModule, branchName, baseRef, projectName, stackTemplate, repoName, owner, visibility, confirmRepoName,
                createGithub, ci, dockerCompose, scopeDiffersReason, null);
    }
}
