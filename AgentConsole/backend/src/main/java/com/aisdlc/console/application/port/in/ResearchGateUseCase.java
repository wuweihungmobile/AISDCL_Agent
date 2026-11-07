package com.aisdlc.console.application.port.in;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Caller;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;

import java.util.UUID;

/**
 * 內環閘登錄用例（API-RP-23；AC-R2P-15-6；D-138 Q-2／Q-3、D-139、D-142 ⚖P2-6／9）：輸入閘與服務層前置（<b>零 Bridge 請求</b>）通過後，
 * Bridge {@code :gates} 恰一次、不重試。console-api 不判斷審查者獨立性、不比對 digest（漂移由 Bridge 回 422 {@code digest_mismatch}，原樣透傳）。
 */
public interface ResearchGateUseCase {

    /** 可登錄的閘（RELEASE_READY 的 PASS 只經建立 Release Tag）。 */
    enum Gate {
        PR_REVIEW, RTM_VERIFY, RELEASE_READY
    }

    /** 決定。 */
    enum Result {
        PASS, FAIL
    }

    /**
     * 請求本文。{@code gate} 與 {@code result} 以字串收進來（OpenAPI 以 {@code allowableValues} 宣告成列舉）：未知值要由輸入閘回 422 {@code invalid_request}，
     * 若直接綁列舉型別，Jackson 的反序列化失敗會變成 400。
     */
    @Schema(name = "GateRegisterRequest", description = "登錄內環閘決定：FAIL 必填 reason；PR_REVIEW 須 reviewerIndependent＝true；RELEASE_READY 的 PASS 只經 delivery/tag")
    record GateInput(@Schema(allowableValues = {"PR_REVIEW", "RTM_VERIFY", "RELEASE_READY"}, requiredMode = Schema.RequiredMode.REQUIRED) String gate, @Schema(allowableValues = {"PASS", "FAIL"}, requiredMode = Schema.RequiredMode.REQUIRED) String result, @Schema(description = "FAIL 必填；1～500 字", requiredMode = Schema.RequiredMode.NOT_REQUIRED, nullable = true) String reason, @Schema(description = "審查報告參照，至多 300 字", requiredMode = Schema.RequiredMode.NOT_REQUIRED, nullable = true) String reviewReportRef, @Schema(description = "PR_REVIEW 必須為 true（Console 不判斷獨立性）", requiredMode = Schema.RequiredMode.NOT_REQUIRED, nullable = true) Boolean reviewerIndependent) {
    }

    /** Bridge 的流程游標（{@code step、phase、status、detail}）。 */
    @Schema(name = "ResearchFlowCursor", description = "研究工作流的 DB 游標（step、phase、status、detail）")
    @JsonInclude(JsonInclude.Include.ALWAYS)
    record FlowCursor(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) String step, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String phase, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String status, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String detail) {
    }

    @Schema(name = "GateRegisterResult", description = "閘登錄結果；escalated 由 Bridge 回傳值如實帶出（nextState 以 ESCALATION 起頭）")
    @JsonInclude(JsonInclude.Include.ALWAYS)
    record GateResult(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) String gateDecisionId, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Gate gate, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Result result, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String fsmStateBefore, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String nextState, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean escalated, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) FlowCursor flow,
            @Schema(requiredMode = Schema.RequiredMode.NOT_REQUIRED, description = "同一 decisionId 重送時 Bridge 回 true（冪等重放；此時 fsmStateBefore 為 null）；一般登錄不出現") @JsonInclude(JsonInclude.Include.NON_NULL) Boolean replayed) {
    }

    GateResult register(Caller caller, UUID researchId, GateInput input);
}
