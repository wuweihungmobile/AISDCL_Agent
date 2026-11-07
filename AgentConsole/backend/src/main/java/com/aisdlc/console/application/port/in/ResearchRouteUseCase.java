package com.aisdlc.console.application.port.in;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Caller;
import com.aisdlc.console.domain.model.research.ResearchRouteViews.Route;

import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * 分流用例（API-RP-14；PRD FR-R2P-11～13；契約 §1.4）：預演（OPERATOR 以上、零副作用）、確認（僅 ADMIN：<b>先建</b> Console {@code projects} 列、再同步呼叫 Bridge
 * {@code :route}、失敗補償到安全態）與讀取最新一筆分流。console-api 對 {@code console.research_*} 零寫入：研究表只有 Bridge 寫，這裡只寫自己的 {@code projects} 與 {@code audit_log}。
 */
public interface ResearchRouteUseCase {

    /**
     * 分流請求（預演與確認同一組欄位；{@code retry} 只有確認用）。欄位可為 null＝請求沒給（預設值由 Bridge 補）。{@code approver}、{@code github_token}、
     * {@code console_project_id} 不在這裡：approver 取 JWT subject、token 取後端設定、專案 id 由服務先建後帶入。
     */
    record RouteInput(String track, String targetModule, String branchName, String baseRef, String projectName, String stackTemplate, String repoName,
                      String owner, String visibility, String confirmRepoName, Boolean createGithub, Boolean ci, Boolean dockerCompose,
                      String scopeDiffersReason, Boolean retry) {
    }

    /** 預演：回 Bridge 的 200 本文（snake_case 動作清單、{@code execution_path}、{@code impl_fsm_project}…）；零 DB 寫入。 */
    Map<String, Object> preview(Caller caller, UUID researchId, RouteInput input);

    /** 確認執行：成功回自 DB 重讀的最新分流（含步驟）；失敗已補償並丟出（Bridge 的 reason、details 逐字）。 */
    Route confirm(Caller caller, UUID researchId, RouteInput input);

    /** 最新一筆分流（含步驟）；尚無分流＝empty（API 回 200 的 {@code null}，D-106）。研究專案不存在丟 404。 */
    Optional<Route> current(UUID researchId);
}
