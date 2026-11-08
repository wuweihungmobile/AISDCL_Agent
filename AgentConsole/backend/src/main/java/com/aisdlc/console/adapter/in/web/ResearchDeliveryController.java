package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Caller;
import com.aisdlc.console.application.port.in.ResearchDeliveryUseCase;
import com.aisdlc.console.domain.model.auth.Role;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.OffsetDateTime;
import java.util.UUID;

/** 交付（API-RP-17／28）：概覽與追溯表（VIEWER 以上可讀）、Release Tag 與 Pull Request（僅 ADMIN）。 */
@RestController
@RequestMapping("/api/v1/research/projects/{id}/delivery")
@Tag(name = "研發工作流（ResearchToPRD）")
public class ResearchDeliveryController {

    private static final String WRITE_FLOW = "失敗序：研究寫入權杖未設 503 → 輸入閘 422 → 專案不存在 404 → 服務層前置 409（零 Bridge 請求）→ Bridge 恰一次（讀取逾時 330 秒、不重試；"
            + "Bridge 的 409／422／502 reason 與 details 逐字透傳，連線失敗 502 bridge_unreachable、逾時 504 bridge_timeout）。approver 與 requestedBy 取 JWT subject。";

    private final ResearchDeliveryUseCase delivery;

    public ResearchDeliveryController(ResearchDeliveryUseCase delivery) {
        this.delivery = delivery;
    }

    @GetMapping
    @Operation(operationId = "getResearchDelivery", summary = "交付概覽（API-RP-17；VIEWER 以上；JDBC 唯讀）",
            description = "回交付列、追溯快照（relPath、sha256；尚無 Tag 為 null）、專案根目錄、containerMode 與交付前置（releaseReady、rtmFull、scrOpen；hasOrigin 與 ghAvailable 未知為 null）。"
                    + "專案不存在＝404 research_not_found。")
    public ApiResult<ResearchDeliveryUseCase.Overview> overview(@Parameter(description = "研究專案 id（UUID）") @PathVariable UUID id) {
        return ApiResult.ok(delivery.overview(id));
    }

    @GetMapping("/traceability")
    @Operation(operationId = "getResearchTraceability", summary = "追溯表預演（API-RP-17；VIEWER 以上；零副作用）",
            description = "轉送 Bridge :traceability-preview：回 {rows[], totals{acTotal, covered, uncovered, frTotal}, rtm{runId, fullyCovered, acPct, advisory}｜null, generatedAt}。"
                    + "凍結 PRD 讀不到＝409 fsm_state_conflict（unmet：prd_not_frozen）；研究寫入權杖未設＝503 research_write_disabled（與分流預演同一家族）。")
    public ApiResult<ResearchDeliveryUseCase.Traceability> traceability(@PathVariable UUID id) {
        return ApiResult.ok(delivery.traceability(id));
    }

    @PostMapping("/tag")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(operationId = "createResearchTag", summary = "建立 Release Tag（API-RP-28；僅 ADMIN）",
            description = "本文 {tagName（semver，至多 64 字）, message?（至多 200 字）, push?（預設 false）, createGithubRelease?（true＝422 release_not_supported）}。"
                    + "前置（409 fsm_state_conflict，details.unmet：not_release_ready、rtm_below_100、scr_open、no_console_project；零 Bridge 請求）。201 回 {delivery, snapshot, flow, fsmState}。"
                    + "Bridge 的 409 tag_exists、502 delivery_step_failed（details.failure_step）、422 digest_mismatch、422 route_unsupported_in_deployment 原樣透傳。" + WRITE_FLOW)
    public ApiResult<ResearchDeliveryUseCase.TagResult> tag(@PathVariable UUID id, @RequestBody ResearchDeliveryUseCase.TagInput request, Authentication authentication) {
        return new ApiResult<>(HttpStatus.CREATED.value(), "success", delivery.tag(caller(authentication), id, request), OffsetDateTime.now(),
                MDC.get("traceId"));
    }

    @PostMapping("/pr")
    @Operation(operationId = "createResearchPr", summary = "建立 Pull Request（API-RP-28；僅 ADMIN）",
            description = "本文 {branch?, title?, bodyPreviewAck}；bodyPreviewAck 缺或為 false＝422 preview_ack_required（Bridge 請求 0）。GitHub token 取後端設定鍵 research.github_token，"
                    + "只放進本端點的 Bridge 請求，不入任何回應、日誌與稽核。回 {delivery, created}。" + WRITE_FLOW)
    public ApiResult<ResearchDeliveryUseCase.PrResult> pr(@PathVariable UUID id, @RequestBody ResearchDeliveryUseCase.PrInput request, Authentication authentication) {
        return ApiResult.ok(delivery.pr(caller(authentication), id, request));
    }

    private static Caller caller(Authentication authentication) {
        boolean admin = authentication != null && authentication.getAuthorities().stream().map(GrantedAuthority::getAuthority)
                .anyMatch(("ROLE_" + Role.ADMIN.name())::equals);
        return new Caller(authentication == null ? null : authentication.getName(), admin);
    }
}
