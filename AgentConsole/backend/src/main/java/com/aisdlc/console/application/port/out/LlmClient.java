package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.imports.ParsedResult;

/**
 * OpenAI 相容 chat completions 的出站埠（匯入路徑 B；契約 §3.3.3）。
 *
 * <p>實作負責：呼叫 {@code POST <apiUrl>}（{@code apiUrl} 就是完整端點，<b>原樣</b> POST、不補任何路徑，AR-09）、
 * 取 {@code choices[0].message.content}、剝除外層 ``` 程式碼框、把 JSON 轉成三層樹草稿。
 * 草稿只含 {@code project} 與 {@code goals}（欄位可能缺漏、{@code key}／{@code passCriteria} 可能空白——
 * 補 key、補佔位字串、以 ParseOptions 覆寫 executionPath 與有界閘由用例負責）。
 */
public interface LlmClient {

    /**
     * @param apiUrl         完整的 chat-completions 端點 URL（已通過 SEC-04 規則 1～5；連線前實作會再做規則 6）
     * @param apiKey         解密後的金鑰（絕不寫日誌）
     * @param timeoutSeconds 總逾時（{@code model.timeout}）
     */
    record LlmRequest(String apiUrl, String apiKey, String model, String systemMessage, String userMessage,
                      double temperature, double topP, int maxTokens, int timeoutSeconds) {
    }

    /**
     * @param draft     模型輸出轉成的草稿（只有 project／goals）
     * @param tokenUsed {@code usage.total_tokens}（缺則 prompt＋completion，再缺為 null）
     * @param model     回應的 {@code model}（缺則 null，由呼叫端退回 {@code model.name}）
     */
    record LlmResult(ParsedResult draft, Long tokenUsed, String model) {
    }

    /** 呼叫失敗：{@code UNSUPPORTED}→閘 brain_unsupported；{@code FAILED}→閘 brain_failed。{@code detail} 不含金鑰與完整 URL。 */
    final class LlmException extends RuntimeException {

        private static final long serialVersionUID = 1L;

        /** 失敗種類。 */
        public enum Kind { UNSUPPORTED, FAILED }

        private final Kind kind;

        public LlmException(Kind kind, String detail) {
            super(detail);
            this.kind = kind;
        }

        public Kind kind() {
            return kind;
        }

        public String detail() {
            return getMessage();
        }
    }

    LlmResult generate(LlmRequest request);
}
