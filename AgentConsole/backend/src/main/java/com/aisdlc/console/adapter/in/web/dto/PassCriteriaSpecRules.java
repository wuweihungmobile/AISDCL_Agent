package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.service.PassCriteriaSanitizer;

import java.util.List;
import java.util.Map;

/**
 * NFR-SEC-03：結構化通過標準 {@code passCriteriaSpec} 內若帶有 {@code evaluatorCommand}／
 * {@code expectedOutputRegex}（PRD §5.1.3：它們的 JSONB 封裝，供複合條件），套用與頂層欄位相同的消毒規則，
 * 避免從這個欄位繞過第 1 層驗證。遞迴檢查巢狀物件與陣列；欄位名以路徑表示（例：passCriteriaSpec.all[0].evaluatorCommand）。
 */
final class PassCriteriaSpecRules {

    private static final String ROOT = "passCriteriaSpec";

    private PassCriteriaSpecRules() {
    }

    static void validate(Map<String, Object> spec) {
        if (spec != null) {
            walk(ROOT, spec);
        }
    }

    private static void walk(String path, Object node) {
        if (node instanceof Map<?, ?> map) {
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                String key = String.valueOf(entry.getKey());
                String childPath = path + "." + key;
                Object value = entry.getValue();
                if (value instanceof String text) {
                    if ("evaluatorCommand".equals(key)) {
                        PassCriteriaSanitizer.requireSafeCommand(childPath, text);
                    } else if ("expectedOutputRegex".equals(key)) {
                        PassCriteriaSanitizer.requireCompilableRegex(childPath, text);
                    }
                } else {
                    walk(childPath, value);
                }
            }
        } else if (node instanceof List<?> list) {
            for (int i = 0; i < list.size(); i++) {
                walk(path + "[" + i + "]", list.get(i));
            }
        }
    }
}
