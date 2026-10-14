package com.aisdlc.console.adapter.in.web.dto;

import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.util.Map;

/** DTO 與 domain 之間的 JSON 文字轉換（passCriteriaSpec：API 是 JSON 物件，domain／資料庫存 JSON 文字）。 */
final class JsonSupport {

    private static final JsonMapper MAPPER = JsonMapper.builder().build();
    private static final TypeReference<Map<String, Object>> OBJECT = new TypeReference<>() { };

    private JsonSupport() {
    }

    /** JSON 物件 → 緊湊 JSON 文字；null 或空物件視為「沒有」，回 null（Task 以空白字串表示清除，這裡不用）。 */
    static String toJson(Map<String, Object> value) {
        return value == null ? null : MAPPER.writeValueAsString(value);
    }

    /** JSON 文字 → JSON 物件；null／空白回 null。 */
    static Map<String, Object> toObject(String json) {
        return json == null || json.isBlank() ? null : MAPPER.readValue(json, OBJECT);
    }
}
