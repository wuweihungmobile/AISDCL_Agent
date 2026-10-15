package com.aisdlc.console.application.service;

import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 組 JSON 文字的最小工具（passCriteriaSpec 的落庫形式；test-connection 的探測本文）。為什麼重要：這裡組出的字串會被
 * 當成 JSON 送給外部伺服器或存進 JSONB——任何一個沒跳脫的引號、反斜線或控制字元，都會讓本文壞掉，
 * 更糟的是讓使用者輸入的模型名稱「逃出」字串、注入額外的 JSON 欄位。
 */
class JsonStringsTest {

    @Test
    void quotingEscapesEveryCharacterThatCouldBreakOutOfAJsonString() {
        assertThat(JsonStrings.quote("plain")).isEqualTo("\"plain\"");
        assertThat(JsonStrings.quote("a\"b")).isEqualTo("\"a\\\"b\"");
        assertThat(JsonStrings.quote("a\\b")).isEqualTo("\"a\\\\b\"");
        assertThat(JsonStrings.quote("l1\nl2\r\t\b\f")).isEqualTo("\"l1\\nl2\\r\\t\\b\\f\"");
        assertThat(JsonStrings.quote("\u0001\u001f")).isEqualTo("\"\\u0001\\u001f\"");
        assertThat(JsonStrings.quote("  ")).as("JSON 合法但 JavaScript 不合法的行分隔字元")
                .isEqualTo("\"\\u2028\\u2029\"");
        assertThat(JsonStrings.quote("中文與 emoji 😀")).as("一般 Unicode 原樣").isEqualTo("\"中文與 emoji 😀\"");
        assertThat(JsonStrings.quote("")).isEqualTo("\"\"");
    }

    @Test
    void aModelNameThatTriesToCloseTheStringIsKeptInsideIt() {
        String hostile = "m\",\"max_tokens\":99999,\"x\":\"";
        String body = "{\"model\":" + JsonStrings.quote(hostile) + ",\"max_tokens\":1}";
        assertThat(body).isEqualTo("{\"model\":\"m\\\",\\\"max_tokens\\\":99999,\\\"x\\\":\\\"\",\"max_tokens\":1}");
    }

    @Test
    void aTreeOfMapsListsAndScalarsIsSerializedCompactlyInOrder() {
        Map<String, Object> tree = new LinkedHashMap<>();
        tree.put("source", "sdd");
        tree.put("weakRegex", false);
        tree.put("count", 3);
        tree.put("ratio", 0.5);
        tree.put("none", null);
        tree.put("steps", List.of("a", Map.of("k", "v")));
        tree.put("nested", Map.of("inner", List.of(1, 2)));

        assertThat(JsonStrings.toJson(tree)).isEqualTo("{\"source\":\"sdd\",\"weakRegex\":false,\"count\":3,"
                + "\"ratio\":0.5,\"none\":null,\"steps\":[\"a\",{\"k\":\"v\"}],\"nested\":{\"inner\":[1,2]}}");
    }

    @Test
    void keysAreEscapedTooAndUnknownObjectsFallBackToTheirStringForm() {
        Map<String, Object> tree = new LinkedHashMap<>();
        tree.put("we\"ird", new StringBuilder("sb"));
        assertThat(JsonStrings.toJson(tree)).isEqualTo("{\"we\\\"ird\":\"sb\"}");
        assertThat(JsonStrings.toJson(null)).isEqualTo("null");
        assertThat(JsonStrings.toJson(List.of())).isEqualTo("[]");
        assertThat(JsonStrings.toJson(Map.of())).isEqualTo("{}");
        assertThat(JsonStrings.toJson("text")).isEqualTo("\"text\"");
        assertThat(JsonStrings.toJson(42)).isEqualTo("42");
    }
}
