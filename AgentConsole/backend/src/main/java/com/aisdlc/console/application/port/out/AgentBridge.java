package com.aisdlc.console.application.port.out;

import java.time.Duration;
import java.util.List;
import java.util.Map;

/**
 * Engine Bridge 的出站埠（契約 §3.1 呼叫總表；Bridge 只有 console-api 以服務身分呼叫，內網、無認證）。
 *
 * <p>本棒（W3-B1）只放匯入需要的四個方法：{@code decompose}、{@code approveDraft}、{@code sddCompile}、{@code health}；
 * 第二棒（W3-B2）在<b>同一介面</b>補 runs 系列（{@code startRun}、{@code pauseRun}…，方法名照契約 §3.1 最後一欄）。
 *
 * <p>錯誤約定：連線失敗 → {@code UpstreamException.Unavailable}（502）；讀取逾時 → {@code UpstreamException.TimedOut}
 * （504）；Bridge 回 5xx → {@code UpstreamException.Failure}（502，details 帶 bridgeStatus／bridgeReason）；
 * Bridge 回 4xx → {@link BridgeRejectedException}（由用例依端點語意對映成 409／422…，契約 §3.2）。
 */
public interface AgentBridge {

    /**
     * 路徑 C 的拆解請求（{@code POST /autoclaude/decompose}）。
     *
     * @param minimaxOverrides {@code config_overrides.minimax}（base_url／model／timeout_seconds）；沒有金鑰時為 null
     */
    record DecomposeRequest(String goal, String context, String project, int maxSteps,
                            Map<String, Object> minimaxOverrides) {
    }

    /** Bridge decompose 回傳的步驟（{@code playbook.tasks[]}；已是拓撲序，不含依賴資訊）。 */
    record DraftStep(String stepId, String name, String prompt, String evaluatorCommand) {
    }

    record DecomposeResult(String draftId, String reasoning, List<DraftStep> steps) {
    }

    /**
     * {@code /sdd/compile} 回傳的任務（{@code SddToPlaybookAdapter.compile_tasks} 的 PlaybookTask）。
     *
     * @param weakRegex Bridge 的 {@code weak_regex}：規格的驗收 regex 被判定為太弱
     */
    record SddTask(String stepId, String name, String prompt, String expectedOutputRegex, String evaluatorCommand,
                   boolean weakRegex) {
    }

    record SddCompileResult(String scenario, String specPath, String digest, List<SddTask> tasks) {
    }

    /** 健康探測結果（{@code GET {autoclaude.healthCheckPath}}）；B2 的探測環與通知摘要使用。 */
    record BridgeHealth(boolean ok, int httpStatus) {
    }

    /** Bridge 回了 4xx：帶回它的錯誤封包欄位（{@code {code,reason,gate?,detail?,violations?,…}}）。 */
    final class BridgeRejectedException extends RuntimeException {

        private static final long serialVersionUID = 1L;

        private final int status;
        private final String reason;
        private final String gate;
        private final String detail;
        private final transient List<Map<String, Object>> violations;
        private final transient Map<String, Object> body;

        public BridgeRejectedException(int status, String reason, String gate, String detail,
                                       List<Map<String, Object>> violations, Map<String, Object> body) {
            super("Bridge 回應 " + status + " " + reason);
            this.status = status;
            this.reason = reason;
            this.gate = gate;
            this.detail = detail;
            this.violations = violations == null ? List.of() : List.copyOf(violations);
            this.body = body == null ? Map.of() : Map.copyOf(body);
        }

        public int status() {
            return status;
        }

        /** Bridge 的 {@code reason}（例：{@code spec_not_found}、{@code draft_not_found}）；沒有則為空字串。 */
        public String reason() {
            return reason;
        }

        /** 有界閘名稱（decompose 的 422）；沒有則為 null。 */
        public String gate() {
            return gate;
        }

        public String detail() {
            return detail;
        }

        public List<Map<String, Object>> violations() {
            return violations;
        }

        /** 完整的 Bridge 錯誤本文（轉成 details 時逐項原樣帶出）。 */
        public Map<String, Object> body() {
            return body;
        }
    }

    /**
     * 路徑 C：{@code POST /autoclaude/decompose}。
     *
     * @param readTimeout 讀取逾時（契約 §3.1：{@code model.timeout}＋15 秒）
     */
    DecomposeResult decompose(DecomposeRequest request, Duration readTimeout);

    /** signoff 路徑 C：{@code POST /autoclaude/decompose/{draft_id}:approve}；Bridge 的 409 {@code already_signed_off} 由呼叫端視為成功。 */
    void approveDraft(String draftId, String approver);

    /** 路徑 A：{@code POST /sdd/compile {spec_dir}}。 */
    SddCompileResult sddCompile(String specDir);

    /** 健康探測（不丟例外：連不上就是 {@code ok=false}）。 */
    BridgeHealth health();
}
