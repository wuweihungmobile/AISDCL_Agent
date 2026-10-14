package com.aisdlc.console.support;

import com.jayway.jsonpath.DocumentContext;
import com.jayway.jsonpath.JsonPath;
import com.jayway.jsonpath.PathNotFoundException;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import tools.jackson.databind.json.JsonMapper;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

/**
 * 整合測試用的 HTTP 小幫手：包 MockMvc（走完整 Security filter chain，不繞過任何過濾器），
 * 回應以 JsonPath 讀取。{@code token} 傳 null＝匿名。
 */
public final class ApiClient {

    private static final JsonMapper JSON = JsonMapper.builder().build();

    private final MockMvc mvc;

    public ApiClient(MockMvc mvc) {
        this.mvc = mvc;
    }

    public Resp get(String token, String url) {
        return send(token, MockMvcRequestBuilders.get(url));
    }

    public Resp delete(String token, String url) {
        return send(token, MockMvcRequestBuilders.delete(url));
    }

    public Resp post(String token, String url, Object body) {
        return send(token, MockMvcRequestBuilders.post(url).contentType(MediaType.APPLICATION_JSON)
                .content(toJson(body)));
    }

    /** 不帶本文的 POST（例如 retry）。 */
    public Resp post(String token, String url) {
        return send(token, MockMvcRequestBuilders.post(url));
    }

    public Resp put(String token, String url, Object body) {
        return send(token, MockMvcRequestBuilders.put(url).contentType(MediaType.APPLICATION_JSON)
                .content(toJson(body)));
    }

    /** 送出任意原始字串當本文（用來測畸形 JSON）。 */
    public Resp raw(String token, HttpMethod method, String url, String rawBody) {
        return send(token, MockMvcRequestBuilders.request(method, url).contentType(MediaType.APPLICATION_JSON)
                .content(rawBody));
    }

    public Resp send(String token, MockHttpServletRequestBuilder builder) {
        if (token != null) {
            builder.header(HttpHeaders.AUTHORIZATION, "Bearer " + token);
        }
        try {
            return new Resp(mvc.perform(builder).andReturn());
        } catch (Exception e) {
            throw new IllegalStateException("MockMvc 呼叫失敗", e);
        }
    }

    public static String toJson(Object body) {
        return body instanceof String s ? s : JSON.writeValueAsString(body);
    }

    /** 一次回應；json／data 以 JsonPath 讀取。 */
    public static final class Resp {

        private final MvcResult result;
        private final String body;
        private DocumentContext json;

        Resp(MvcResult result) {
            this.result = result;
            this.body = new String(result.getResponse().getContentAsByteArray(), StandardCharsets.UTF_8);
        }

        public int status() {
            return result.getResponse().getStatus();
        }

        public String body() {
            return body;
        }

        public String header(String name) {
            return result.getResponse().getHeader(name);
        }

        /** 讀 JsonPath（例：{@code "$.data.id"}、{@code "$.errors[*].field"}）。 */
        public <T> T read(String path) {
            if (json == null) {
                json = JsonPath.parse(body);
            }
            return json.read(path);
        }

        public boolean has(String path) {
            try {
                return read(path) != null;
            } catch (PathNotFoundException e) {
                return false;
            }
        }

        public String id() {
            return read("$.data.id");
        }

        public List<String> errorFields() {
            return read("$.errors[*].field");
        }

        public Map<String, Object> data() {
            return read("$.data");
        }
    }
}
