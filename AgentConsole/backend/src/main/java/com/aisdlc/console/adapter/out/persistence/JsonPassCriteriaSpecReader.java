package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.PassCriteriaSpecReader;
import com.aisdlc.console.domain.model.execution.SddTaskSpec;
import org.springframework.stereotype.Component;
import tools.jackson.core.JacksonException;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.util.Map;

/**
 * {@link PassCriteriaSpecReader} 的 Jackson 實作（domain 與 application 不依賴 JSON 函式庫，解析放在 persistence 介面卡）。
 * 容錯：本文不是 JSON 物件、JSON 壞掉、或欄位型別不對，一律當「沒有」——一個壞掉的 {@code passCriteriaSpec} 只代表「不是 SDD 來源」，
 * 不該讓 execute 變成 500。
 */
@Component
class JsonPassCriteriaSpecReader implements PassCriteriaSpecReader {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final TypeReference<Map<String, Object>> OBJECT = new TypeReference<>() { };

    @Override
    public SddTaskSpec read(String passCriteriaSpecJson) {
        if (passCriteriaSpecJson == null || passCriteriaSpecJson.isBlank()) {
            return SddTaskSpec.NONE;
        }
        Map<String, Object> map;
        try {
            map = JSON.readValue(passCriteriaSpecJson, OBJECT);
        } catch (JacksonException e) {
            return SddTaskSpec.NONE;
        }
        if (map == null) {
            return SddTaskSpec.NONE;
        }
        return new SddTaskSpec(text(map.get("source")), text(map.get("stepId")), text(map.get("specDigest")),
                bool(map.get("weakRegex")), bool(map.get("maintainContext")));
    }

    private static String text(Object value) {
        return value instanceof String s ? s : null;
    }

    private static Boolean bool(Object value) {
        return value instanceof Boolean b ? b : null;
    }
}
