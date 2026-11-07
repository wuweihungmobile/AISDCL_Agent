package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Caller;
import com.aisdlc.console.application.port.in.ResearchGateUseCase;
import com.aisdlc.console.domain.model.auth.Role;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

/** 內環閘登錄（API-RP-23；僅 ADMIN；{@code SecurityConfig} 逐條規則）。 */
@RestController
@RequestMapping("/api/v1/research/projects/{id}")
@Tag(name = "研發工作流（ResearchToPRD）")
public class ResearchGateController {

    private final ResearchGateUseCase gates;

    public ResearchGateController(ResearchGateUseCase gates) {
        this.gates = gates;
    }

    @PostMapping("/gates")
    @Operation(operationId = "registerResearchGate", summary = "登錄內環閘決定（API-RP-23；僅 ADMIN）",
            description = "本文 {gate（PR_REVIEW｜RTM_VERIFY｜RELEASE_READY）, result（PASS｜FAIL）, reason（FAIL 必填，至多 500 字）, reviewReportRef?（至多 300 字）, reviewerIndependent}。"
                    + "RELEASE_READY 的 PASS 只經 POST …/delivery/tag（422 release_pass_via_tag）；PR_REVIEW 須 reviewerIndependent＝true（Console 不判斷獨立性）。"
                    + "失敗序：研究寫入權杖未設 503 → 輸入閘 422 → 專案不存在 404 → 未綁 Console 專案 409（unmet：no_console_project）→ OPEN SCR 409 scr_open → "
                    + "服務層前置 409（unmet：tasks_incomplete、rtm_below_100、rtm_unavailable；零 Bridge 請求）→ Bridge :gates 恰一次（讀取逾時 330 秒、不重試）。"
                    + "凍結 digest 漂移由 Bridge 回 422 digest_mismatch（details.drift），原樣透傳；escalated 由 Bridge 回傳值如實帶出。approver 與 requestedBy 取 JWT subject。")
    public ApiResult<ResearchGateUseCase.GateResult> register(@Parameter(description = "研究專案 id（UUID）") @PathVariable UUID id,
                                                   @RequestBody ResearchGateUseCase.GateInput request, Authentication authentication) {
        return ApiResult.ok(gates.register(caller(authentication), id, request));
    }

    private static Caller caller(Authentication authentication) {
        boolean admin = authentication != null && authentication.getAuthorities().stream().map(GrantedAuthority::getAuthority)
                .anyMatch(("ROLE_" + Role.ADMIN.name())::equals);
        return new Caller(authentication == null ? null : authentication.getName(), admin);
    }
}
