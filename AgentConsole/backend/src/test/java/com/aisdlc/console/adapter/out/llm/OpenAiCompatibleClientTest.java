package com.aisdlc.console.adapter.out.llm;

import com.aisdlc.console.application.port.out.LlmClient.LlmException;
import com.aisdlc.console.application.port.out.LlmClient.LlmRequest;
import com.aisdlc.console.application.port.out.LlmClient.LlmResult;
import com.aisdlc.console.application.port.out.OutboundHttp;
import com.aisdlc.console.application.port.out.OutboundHttp.HttpResult;
import com.aisdlc.console.application.port.out.OutboundHttp.OutboundIoException;
import com.aisdlc.console.domain.model.imports.ParsedResult;
import com.aisdlc.console.domain.service.OutboundUrlPolicy;
import com.aisdlc.console.domain.service.OutboundUrlPolicy.Rejected;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * OpenAI 相容 chat completions 客戶端（匯入路徑 B；契約 §3.3.3）。為什麼重要：模型輸出是不可信的外部輸入——
 * 非 JSON、被截斷、缺欄位、HTTP 錯誤都必須變成「有說明的失敗」而不是半套資料或 500；
 * 失敗訊息不得含金鑰與完整 URL。
 */
class OpenAiCompatibleClientTest {

    private static final String API_KEY = "sk-secret-key-123456";
    private static final String URL = "https://api.minimax.io/v1/text/chatcompletion_v2?tenant=private";

    /** 記錄送出內容、回傳預設結果的假外呼。 */
    private static final class FakeOutbound implements OutboundHttp {
        final List<String> urls = new ArrayList<>();
        final List<Map<String, String>> headers = new ArrayList<>();
        final List<String> bodies = new ArrayList<>();
        final List<Duration> timeouts = new ArrayList<>();
        Supplier<HttpResult> reply = () -> new HttpResult(200, "{}", 5, "api.minimax.io");

        @Override
        public HttpResult postJson(String url, Map<String, String> requestHeaders, String jsonBody,
                                   Duration connectTimeout, Duration totalTimeout) {
            urls.add(url);
            headers.add(requestHeaders);
            bodies.add(jsonBody);
            timeouts.add(totalTimeout);
            return reply.get();
        }
    }

    private final FakeOutbound outbound = new FakeOutbound();
    private final OpenAiCompatibleClient client = new OpenAiCompatibleClient(outbound);

    private static LlmRequest request() {
        return new LlmRequest(URL, API_KEY, "e2e-model", "系統訊息", "使用者訊息", 0.3, 0.9, 8192, 30);
    }

    private static String completion(String content, String finishReason, String usageJson, String model) {
        String escaped = content.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
                .replace("\r", "\\r").replace("\t", "\\t");
        return "{\"id\":\"c1\",\"object\":\"chat.completion\"" + (model == null ? "" : ",\"model\":\"" + model + "\"")
                + ",\"choices\":[{\"index\":0,\"finish_reason\":\"" + finishReason + "\",\"message\":{\"role\":"
                + "\"assistant\",\"content\":\"" + escaped + "\"}}]" + (usageJson == null ? "" : ",\"usage\":" + usageJson)
                + "}";
    }

    private static final String DRAFT = "{\"project\":{\"name\":\"E2E 匯入專案\",\"executionPath\":\"/ignored\","
            + "\"passCriteria\":\"三個目標全部完成\",\"description\":\"由 BRD 匯入\"},\"goals\":[{\"key\":\"g1\","
            + "\"name\":\"基礎\",\"description\":\"\",\"passCriteria\":\"基礎任務完成\",\"sortOrder\":0,"
            + "\"dependsOn\":[],\"tasks\":[{\"name\":\"初始化\",\"description\":\"請輸出 [T1_DONE]\","
            + "\"passCriteria\":\"輸出含 [T1_DONE]\",\"sortOrder\":0,\"estimatedTokens\":120},"
            + "{\"name\":\"設定\",\"description\":\"請輸出 [T2_DONE]\",\"passCriteria\":\"輸出含 [T2_DONE]\"}]},"
            + "{\"key\":\"g2\",\"name\":\"核心\",\"passCriteria\":\"核心完成\",\"dependsOn\":[\"g1\"],"
            + "\"tasks\":[{\"name\":\"實作\",\"description\":\"請輸出 [T3_DONE]\",\"passCriteria\":\"輸出含 [T3_DONE]\"}]}]}";

    private void replyWith(String body) {
        outbound.reply = () -> new HttpResult(200, body, 5, "api.minimax.io");
    }

    private LlmException failure() {
        return org.assertj.core.api.Assertions.catchThrowableOfType(LlmException.class, () -> client.generate(request()));
    }

    // ── 請求 ─────────────────────────────────────────────────────────────────

    @Test
    void theRequestIsPostedToTheExactConfiguredUrlWithBearerAuthAndTheOpenAiBody() {
        replyWith(completion(DRAFT, "stop", "{\"total_tokens\":1152}", "e2e-model"));
        client.generate(request());

        assertThat(outbound.urls).containsExactly(URL);
        assertThat(outbound.headers.get(0)).containsEntry("Authorization", "Bearer " + API_KEY)
                .containsEntry("Content-Type", "application/json");
        assertThat(outbound.timeouts.get(0)).isEqualTo(Duration.ofSeconds(30));
        String body = outbound.bodies.get(0);
        assertThat(JsonPath.<String>read(body, "$.model")).isEqualTo("e2e-model");
        assertThat(JsonPath.<Boolean>read(body, "$.stream")).isFalse();
        assertThat(JsonPath.<String>read(body, "$.response_format.type")).isEqualTo("json_object");
        assertThat(JsonPath.<String>read(body, "$.messages[0].role")).isEqualTo("system");
        assertThat(JsonPath.<String>read(body, "$.messages[0].content")).isEqualTo("系統訊息");
        assertThat(JsonPath.<String>read(body, "$.messages[1].role")).isEqualTo("user");
        assertThat(JsonPath.<String>read(body, "$.messages[1].content")).isEqualTo("使用者訊息");
        assertThat(JsonPath.<Double>read(body, "$.temperature")).isEqualTo(0.3);
        assertThat(JsonPath.<Double>read(body, "$.top_p")).isEqualTo(0.9);
        assertThat(JsonPath.<Integer>read(body, "$.max_tokens")).isEqualTo(8192);
    }

    // ── 成功解析 ─────────────────────────────────────────────────────────────

    @Test
    void aWellFormedAnswerBecomesAThreeLayerDraftWithTokenUsageAndModel() {
        replyWith(completion(DRAFT, "stop", "{\"prompt_tokens\":812,\"completion_tokens\":340,\"total_tokens\":1152}",
                "e2e-model"));
        LlmResult result = client.generate(request());

        assertThat(result.tokenUsed()).isEqualTo(1152L);
        assertThat(result.model()).isEqualTo("e2e-model");
        ParsedResult draft = result.draft();
        assertThat(draft.project().name()).isEqualTo("E2E 匯入專案");
        assertThat(draft.project().executionPath()).as("原樣交給用例，由用例以 ParseOptions 覆寫").isEqualTo("/ignored");
        assertThat(draft.goals()).hasSize(2);
        assertThat(draft.goals().get(0).tasks()).hasSize(2);
        assertThat(draft.goals().get(0).tasks().get(0).estimatedTokens()).isEqualTo(120L);
        assertThat(draft.goals().get(1).dependsOn()).containsExactly("g1");
        assertThat(draft.goals().get(1).tasks().get(0).description()).isEqualTo("請輸出 [T3_DONE]");
    }

    @Test
    void anOuterMarkdownFenceIsStrippedWithOrWithoutTheLanguageTag() {
        for (String fenced : new String[] {"```json\n" + DRAFT + "\n```", "```\n" + DRAFT + "\n```",
                "  ```JSON\r\n" + DRAFT + "\r\n```  "}) {
            replyWith(completion(fenced, "stop", null, null));
            assertThat(client.generate(request()).draft().goals()).hasSize(2);
        }
    }

    @Test
    void stripFenceOnlyTouchesAnOuterFence() {
        assertThat(OpenAiCompatibleClient.stripFence("{\"a\":\"```\"}")).isEqualTo("{\"a\":\"```\"}");
        assertThat(OpenAiCompatibleClient.stripFence("```json\n{}\n```")).isEqualTo("{}");
        assertThat(OpenAiCompatibleClient.stripFence("```")).isEmpty();
    }

    @Test
    void tokenUsageFallsBackToPromptPlusCompletionAndThenToNull() {
        replyWith(completion(DRAFT, "stop", "{\"prompt_tokens\":10,\"completion_tokens\":5}", null));
        assertThat(client.generate(request()).tokenUsed()).isEqualTo(15L);
        replyWith(completion(DRAFT, "stop", null, null));
        LlmResult none = client.generate(request());
        assertThat(none.tokenUsed()).isNull();
        assertThat(none.model()).isNull();
    }

    @Test
    void missingOptionalFieldsAreLeftNullForTheUseCaseToFill() {
        replyWith(completion("{\"project\":{\"name\":\"P\"},\"goals\":[{\"name\":\"G\",\"tasks\":[{\"name\":\"T\"}]}]}",
                "stop", null, null));
        ParsedResult draft = client.generate(request()).draft();
        assertThat(draft.goals().get(0).key()).isNull();
        assertThat(draft.goals().get(0).passCriteria()).isNull();
        assertThat(draft.goals().get(0).tasks().get(0).description()).isNull();
        assertThat(draft.goals().get(0).dependsOn()).isEmpty();
    }

    // ── 失敗 ─────────────────────────────────────────────────────────────────

    @Test
    void aTruncatedAnswerSaysHowToFixIt() {
        replyWith(completion("{\"project\":", "length", null, null));
        LlmException e = failure();
        assertThat(e.kind()).isEqualTo(LlmException.Kind.FAILED);
        assertThat(e.detail()).contains("被截斷", "model.maxTokensPerRequest");
    }

    @Test
    void emptyAndNonJsonContentFailWithAnExplanation() {
        replyWith(completion("", "stop", null, null));
        assertThat(failure().detail()).contains("模型輸出為空");
        replyWith(completion("not json", "stop", null, null));
        assertThat(failure().detail()).startsWith("模型輸出不是合法 JSON");
        replyWith("this is not an envelope");
        assertThat(failure().detail()).startsWith("模型回應不是合法 JSON");
        replyWith("{}");
        assertThat(failure().detail()).contains("模型輸出為空");
    }

    @Test
    void missingProjectMissingOrEmptyGoalsAndEmptyTasksAreEachNamed() {
        replyWith(completion("{\"goals\":[{\"name\":\"G\",\"tasks\":[{\"name\":\"T\"}]}]}", "stop", null, null));
        assertThat(failure().detail()).contains("缺少 project");
        replyWith(completion("{\"project\":{\"name\":\"P\"}}", "stop", null, null));
        assertThat(failure().detail()).contains("goals");
        replyWith(completion("{\"project\":{\"name\":\"P\"},\"goals\":[]}", "stop", null, null));
        assertThat(failure().detail()).contains("goals");
        replyWith(completion("{\"project\":{\"name\":\"P\"},\"goals\":[{\"name\":\"空目標\",\"tasks\":[]}]}", "stop",
                null, null));
        assertThat(failure().detail()).contains("空目標", "goals[0].tasks");
    }

    @Test
    void httpErrorsCarryOnlyTheStatusNeverTheKeyOrTheUrl() {
        for (int status : new int[] {400, 401, 429, 500, 503}) {
            outbound.reply = () -> new HttpResult(status, "{\"error\":\"" + API_KEY + "\"}", 5, "api.minimax.io");
            LlmException e = failure();
            assertThat(e.kind()).isEqualTo(LlmException.Kind.FAILED);
            assertThat(e.detail()).contains("HTTP " + status).doesNotContain(API_KEY).doesNotContain("tenant=private")
                    .doesNotContain("api.minimax.io");
        }
    }

    @Test
    void aRedirectIsReportedAsRefusedToFollow() {
        outbound.reply = () -> new HttpResult(302, "", 5, "api.minimax.io");
        assertThat(failure().detail()).contains("302").contains("拒絕跟隨");
    }

    @Test
    void networkFailuresAreTimeoutOrConnectionExplanationsWithoutLeakingAnything() {
        outbound.reply = () -> {
            throw new OutboundIoException(OutboundIoException.Kind.TIMEOUT, "逾時");
        };
        assertThat(failure().detail()).isEqualTo("呼叫模型逾時（30 秒）");
        outbound.reply = () -> {
            throw new OutboundIoException(OutboundIoException.Kind.CONNECT, "拒絕連線");
        };
        assertThat(failure().detail()).isEqualTo("無法連線到模型：拒絕連線");
    }

    @Test
    void aPolicyRefusalIsUnsupportedNotFailedAndNamesTheViolationOnly() {
        outbound.reply = () -> {
            throw org.assertj.core.api.Assertions.catchThrowableOfType(Rejected.class,
                    () -> new OutboundUrlPolicy(List.of("api.minimax.io"), false).checkStatic("http://10.0.0.5/x"));
        };
        LlmException e = failure();
        assertThat(e.kind()).isEqualTo(LlmException.Kind.UNSUPPORTED);
        assertThat(e.detail()).isEqualTo("模型位址未通過 SSRF／allowlist 檢查（private_ip）");
    }

    @Test
    void aNonObjectDraftAndATopLevelArrayAreFailuresNotCrashes() {
        replyWith(completion("[1,2,3]", "stop", null, null));
        assertThatThrownBy(() -> client.generate(request())).isInstanceOf(LlmException.class);
    }
}
