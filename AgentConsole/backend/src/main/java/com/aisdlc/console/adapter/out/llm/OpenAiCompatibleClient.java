package com.aisdlc.console.adapter.out.llm;

import com.aisdlc.console.application.port.out.LlmClient;
import com.aisdlc.console.application.port.out.OutboundHttp;
import com.aisdlc.console.application.port.out.OutboundHttp.HttpResult;
import com.aisdlc.console.application.port.out.OutboundHttp.OutboundIoException;
import com.aisdlc.console.domain.model.imports.ParsedResult;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedGoal;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedProject;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedTask;
import com.aisdlc.console.domain.service.OutboundUrlPolicy.Rejected;
import org.springframework.stereotype.Component;
import tools.jackson.core.JacksonException;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * OpenAI 相容 chat completions 的 {@link LlmClient}（匯入路徑 B；契約 §3.3.3）。
 *
 * <p>{@code apiUrl} 是<b>完整端點</b>，原樣 {@code POST}（不補任何路徑，AR-09）；連線走 {@link OutboundHttp}
 * （SSRF 政策、釘 IP、不跟 redirect）。失敗的 {@code detail} 只含 HTTP 狀態或例外類別，<b>不含金鑰與完整 URL</b>。
 * 回應處理：取 {@code choices[0].message.content}；{@code finish_reason=length}→被截斷；先剝除外層 ``` 程式碼框
 * 再解析 JSON；缺 {@code project}／{@code goals}、{@code goals} 為空、某目標 {@code tasks} 為空都算失敗。
 */
@Component
class OpenAiCompatibleClient implements LlmClient {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final TypeReference<Map<String, Object>> OBJECT = new TypeReference<>() { };
    private static final Duration CONNECT_TIMEOUT = Duration.ofSeconds(5);

    private final OutboundHttp outbound;

    OpenAiCompatibleClient(OutboundHttp outbound) {
        this.outbound = outbound;
    }

    @Override
    public LlmResult generate(LlmRequest request) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", request.model());
        body.put("messages", List.of(Map.of("role", "system", "content", request.systemMessage()),
                Map.of("role", "user", "content", request.userMessage())));
        body.put("temperature", request.temperature());
        body.put("top_p", request.topP());
        body.put("max_tokens", request.maxTokens());
        body.put("response_format", Map.of("type", "json_object"));
        body.put("stream", false);
        Map<String, String> headers = new LinkedHashMap<>();
        headers.put("Authorization", "Bearer " + request.apiKey());
        headers.put("Content-Type", "application/json");
        headers.put("Accept", "application/json");

        HttpResult http;
        try {
            http = outbound.postJson(request.apiUrl(), headers, JSON.writeValueAsString(body), CONNECT_TIMEOUT,
                    Duration.ofSeconds(request.timeoutSeconds()));
        } catch (Rejected rejected) {
            throw new LlmException(LlmException.Kind.UNSUPPORTED,
                    "模型位址未通過 SSRF／allowlist 檢查（" + rejected.violation().code() + "）");
        } catch (OutboundIoException io) {
            throw new LlmException(LlmException.Kind.FAILED, io.kind() == OutboundIoException.Kind.TIMEOUT
                    ? "呼叫模型逾時（" + request.timeoutSeconds() + " 秒）" : "無法連線到模型：" + io.getMessage());
        }
        if (http.status() < 200 || http.status() >= 300) {
            throw new LlmException(LlmException.Kind.FAILED, http.status() >= 300 && http.status() < 400
                    ? "模型端點回應重新導向（HTTP " + http.status() + "），已拒絕跟隨"
                    : "模型服務回應 HTTP " + http.status());
        }
        Map<String, Object> envelope = parseObject(http.body(), "模型回應不是合法 JSON");
        Map<String, Object> choice = asMap(first(asList(envelope.get("choices"))));
        Map<String, Object> message = asMap(choice.get("message"));
        if ("length".equals(text(choice.get("finish_reason")))) {
            throw failed("輸出被截斷，請縮短文件或調高 model.maxTokensPerRequest");
        }
        String content = text(message.get("content"));
        if (content == null || content.isBlank()) {
            throw failed("模型輸出為空");
        }
        Map<String, Object> draft = parseObject(stripFence(content), "模型輸出不是合法 JSON");
        return new LlmResult(toTree(draft), tokens(asMap(envelope.get("usage"))), text(envelope.get("model")));
    }

    // ── 解析 ──────────────────────────────────────────────────────────────────

    /** 三層樹草稿（欄位可能缺漏；補 key、補佔位字串、以選項覆寫路徑等由用例負責）。 */
    private static ParsedResult toTree(Map<String, Object> doc) {
        if (!(doc.get("project") instanceof Map<?, ?>)) {
            throw failed("模型輸出缺少 project 物件");
        }
        List<?> rawGoals = asList(doc.get("goals"));
        if (rawGoals.isEmpty()) {
            throw failed("模型輸出缺少 goals，或 goals 為空");
        }
        Map<String, Object> p = asMap(doc.get("project"));
        ParsedProject project = new ParsedProject(text(p.get("name")), text(p.get("executionPath")),
                text(p.get("passCriteria")), text(p.get("description")), null);
        List<ParsedGoal> goals = new ArrayList<>();
        for (int i = 0; i < rawGoals.size(); i++) {
            Map<String, Object> g = asMap(rawGoals.get(i));
            List<?> rawTasks = asList(g.get("tasks"));
            String name = text(g.get("name"));
            if (rawTasks.isEmpty()) {
                throw failed("目標「" + (name == null ? "（未命名）" : name) + "」沒有任何任務（goals[" + i + "].tasks 為空）");
            }
            List<ParsedTask> tasks = new ArrayList<>();
            for (int j = 0; j < rawTasks.size(); j++) {
                Map<String, Object> t = asMap(rawTasks.get(j));
                tasks.add(new ParsedTask(text(t.get("name")), text(t.get("description")), text(t.get("passCriteria")),
                        j, longOf(t.get("estimatedTokens")), null, null, null, null));
            }
            List<String> dependsOn = new ArrayList<>();
            for (Object dependency : asList(g.get("dependsOn"))) {
                dependsOn.add(text(dependency));
            }
            goals.add(new ParsedGoal(text(g.get("key")), name, text(g.get("description")),
                    text(g.get("passCriteria")), i, dependsOn, tasks));
        }
        return ParsedResult.tree(project, goals);
    }

    private static Long tokens(Map<String, Object> usage) {
        Long total = longOf(usage.get("total_tokens"));
        if (total != null) {
            return total;
        }
        Long prompt = longOf(usage.get("prompt_tokens"));
        Long completion = longOf(usage.get("completion_tokens"));
        return prompt != null && completion != null ? prompt + completion : null;
    }

    /** 容許外層 ``` 程式碼框（含 {@code ```json}）；其餘內容原樣交給 JSON 解析。 */
    static String stripFence(String content) {
        String s = content.strip();
        if (!s.startsWith("```")) {
            return s;
        }
        int newline = s.indexOf('\n');
        s = newline >= 0 ? s.substring(newline + 1) : "";
        s = s.stripTrailing();
        if (s.endsWith("```")) {
            s = s.substring(0, s.length() - 3);
        }
        return s.strip();
    }

    private static Map<String, Object> parseObject(String json, String failure) {
        try {
            return JSON.readValue(json, OBJECT);
        } catch (JacksonException e) {
            throw failed(failure + "：" + shorten(e.getOriginalMessage()));
        }
    }

    private static LlmException failed(String detail) {
        return new LlmException(LlmException.Kind.FAILED, detail);
    }

    private static String shorten(String message) {
        if (message == null) {
            return "（無說明）";
        }
        String oneLine = message.replaceAll("\\s+", " ").strip();
        return oneLine.length() <= 160 ? oneLine : oneLine.substring(0, 160) + "…";
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> asMap(Object value) {
        return value instanceof Map<?, ?> map ? (Map<String, Object>) map : Map.of();
    }

    private static List<?> asList(Object value) {
        return value instanceof List<?> list ? list : List.of();
    }

    private static Object first(List<?> list) {
        return list.isEmpty() ? null : list.get(0);
    }

    private static String text(Object value) {
        return value == null ? null : value.toString();
    }

    private static Long longOf(Object value) {
        return value instanceof Number number ? Long.valueOf(number.longValue()) : null;
    }
}
