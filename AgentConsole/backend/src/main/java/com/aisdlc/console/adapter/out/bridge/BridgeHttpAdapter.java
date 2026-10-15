package com.aisdlc.console.adapter.out.bridge;

import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.domain.exception.UpstreamException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.client.ClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import tools.jackson.core.JacksonException;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.io.InputStream;
import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.net.UnknownHostException;
import java.net.http.HttpConnectTimeoutException;
import java.net.http.HttpTimeoutException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * {@link AgentBridge} 的 {@code RestClient} 實作（契約 §3.1／§3.2）。Bridge 只有 console-api 以服務身分呼叫
 * （內網、無認證）。每個呼叫各有逾時（{@link RequestFactoryProvider}）；本檔不重試（非冪等呼叫失敗即由上層決定）。
 *
 * <p>錯誤分流：連線失敗 → {@link UpstreamException.Unavailable}；讀取逾時 → {@link UpstreamException.TimedOut}；
 * 5xx → {@link UpstreamException.Failure}；4xx → {@link BridgeRejectedException}（Bridge 的
 * {@code {code,reason,gate?,detail?,violations?}} 封包原樣帶回，由用例依端點語意轉成 409／422…）。
 */
@Component
class BridgeHttpAdapter implements AgentBridge {

    private static final Logger LOG = LoggerFactory.getLogger(BridgeHttpAdapter.class);
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final TypeReference<Map<String, Object>> OBJECT = new TypeReference<>() { };
    private static final Duration CONNECT_TIMEOUT = Duration.ofSeconds(2);
    private static final Duration HEALTH_READ_TIMEOUT = Duration.ofSeconds(3);
    private static final Duration APPROVE_READ_TIMEOUT = Duration.ofSeconds(10);
    private static final Duration COMPILE_READ_TIMEOUT = Duration.ofSeconds(15);
    private static final int MAX_BODY_BYTES = 8 * 1024 * 1024;

    private final RestClient.Builder builder;
    private final BridgeEndpoints endpoints;
    private final RequestFactoryProvider factories;

    BridgeHttpAdapter(RestClient.Builder bridgeRestClientBuilder, BridgeEndpoints endpoints,
                      RequestFactoryProvider factories) {
        this.builder = bridgeRestClientBuilder;
        this.endpoints = endpoints;
        this.factories = factories;
    }

    @Override
    public DecomposeResult decompose(DecomposeRequest request, Duration readTimeout) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("goal", request.goal());
        body.put("context", request.context());
        body.put("project", request.project());
        body.put("max_steps", request.maxSteps());
        if (request.minimaxOverrides() != null) {
            body.put("config_overrides", Map.of("minimax", request.minimaxOverrides()));
        }
        Map<String, Object> doc = postJson(endpoints.autoclaudeBase() + "/autoclaude/decompose", body, readTimeout);
        Map<String, Object> playbook = asMap(doc.get("playbook"));
        List<DraftStep> steps = new ArrayList<>();
        for (Object item : asList(playbook.get("tasks"))) {
            Map<String, Object> task = asMap(item);
            steps.add(new DraftStep(text(task.get("step_id")), text(task.get("name")), text(task.get("prompt")),
                    text(task.get("evaluator_command"))));
        }
        return new DecomposeResult(text(doc.get("draft_id")), text(doc.get("reasoning")), steps);
    }

    @Override
    public void approveDraft(String draftId, String approver) {
        postJson(endpoints.autoclaudeBase() + "/autoclaude/decompose/" + draftId + ":approve",
                Map.of("approver", approver), APPROVE_READ_TIMEOUT);
    }

    @Override
    public SddCompileResult sddCompile(String specDir) {
        Map<String, Object> doc = postJson(endpoints.sddBase() + "/sdd/compile", Map.of("spec_dir", specDir),
                COMPILE_READ_TIMEOUT);
        List<SddTask> tasks = new ArrayList<>();
        for (Object item : asList(doc.get("tasks"))) {
            Map<String, Object> task = asMap(item);
            tasks.add(new SddTask(text(task.get("step_id")), text(task.get("name")), text(task.get("prompt")),
                    text(task.get("expected_output_regex")), text(task.get("evaluator_command")),
                    Boolean.TRUE.equals(task.get("weak_regex"))));
        }
        return new SddCompileResult(text(doc.get("scenario")), text(doc.get("spec_path")), text(doc.get("digest")),
                tasks);
    }

    @Override
    public BridgeHealth health() {
        try {
            int status = client(HEALTH_READ_TIMEOUT).get().uri(endpoints.autoclaudeBase() + endpoints.healthPath())
                    .exchange((request, response) -> response.getStatusCode().value());
            return new BridgeHealth(status >= 200 && status < 300, status);
        } catch (RuntimeException e) {
            LOG.debug("Bridge 健康探測失敗：{}", e.toString());
            return new BridgeHealth(false, 0);
        }
    }

    // ── 內部 ──────────────────────────────────────────────────────────────────

    private RestClient client(Duration readTimeout) {
        RestClient.Builder copy = builder.clone();
        ClientHttpRequestFactory factory = factories.create(CONNECT_TIMEOUT, readTimeout);
        if (factory != null) {
            copy.requestFactory(factory);
        }
        return copy.build();
    }

    private Map<String, Object> postJson(String url, Object body, Duration readTimeout) {
        String payload = JSON.writeValueAsString(body);
        try {
            return client(readTimeout).post().uri(url).contentType(MediaType.APPLICATION_JSON).body(payload)
                    .exchange((request, response) -> handle(response.getStatusCode(), readBody(response.getBody())));
        } catch (ResourceAccessException e) {
            throw translate(e);
        }
    }

    private static Map<String, Object> handle(HttpStatusCode status, String body) {
        if (status.is2xxSuccessful()) {
            return parseObject(body, "Bridge 回了無法解析的成功本文");
        }
        Map<String, Object> error = parseErrorBody(body);
        String reason = text(error.get("reason"));
        if (status.is4xxClientError()) {
            List<Map<String, Object>> violations = new ArrayList<>();
            for (Object item : asList(error.get("violations"))) {
                violations.add(asMap(item));
            }
            throw new BridgeRejectedException(status.value(), reason == null ? "" : reason, text(error.get("gate")),
                    text(error.get("detail")), violations, error);
        }
        Map<String, Object> details = new LinkedHashMap<>();
        details.put("bridgeStatus", status.value());
        if (reason != null && !reason.isEmpty()) {
            details.put("bridgeReason", reason);
        }
        throw new UpstreamException.Failure("Bridge 回了非預期的錯誤（HTTP " + status.value()
                + (reason == null || reason.isEmpty() ? "" : "，" + reason) + "）", details);
    }

    private static UpstreamException translate(ResourceAccessException e) {
        for (Throwable t = e; t != null; t = t.getCause()) {
            if (t instanceof HttpConnectTimeoutException || t instanceof ConnectException
                    || t instanceof UnknownHostException) {
                return new UpstreamException.Unavailable("無法連線到 Engine Bridge：" + t.getClass().getSimpleName());
            }
            if (t instanceof HttpTimeoutException || t instanceof SocketTimeoutException) {
                return new UpstreamException.TimedOut("Engine Bridge 逾時：" + t.getClass().getSimpleName());
            }
        }
        return new UpstreamException.Unavailable("與 Engine Bridge 通訊失敗：" + e.getClass().getSimpleName());
    }

    private static String readBody(InputStream stream) throws IOException {
        byte[] bytes = stream.readNBytes(MAX_BODY_BYTES);
        return new String(bytes, StandardCharsets.UTF_8);
    }

    private static Map<String, Object> parseObject(String body, String failure) {
        try {
            return JSON.readValue(body, OBJECT);
        } catch (JacksonException e) {
            throw new UpstreamException.Failure(failure, Map.of("bridgeStatus", 200));
        }
    }

    /** 錯誤本文解析失敗不應遮蔽真正的狀態碼：退回空物件。 */
    private static Map<String, Object> parseErrorBody(String body) {
        try {
            return body == null || body.isBlank() ? Map.of() : JSON.readValue(body, OBJECT);
        } catch (JacksonException e) {
            return Map.of();
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> asMap(Object value) {
        return value instanceof Map<?, ?> map ? (Map<String, Object>) map : Map.of();
    }

    private static List<?> asList(Object value) {
        return value instanceof List<?> list ? list : List.of();
    }

    private static String text(Object value) {
        return value == null ? null : value.toString();
    }
}
