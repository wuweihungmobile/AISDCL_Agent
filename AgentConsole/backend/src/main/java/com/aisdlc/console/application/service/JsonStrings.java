package com.aisdlc.console.application.service;

import java.util.Map;

/** 組 JSON 文字用的最小工具：把字串安全地放進 JSON 字串字面值、把簡單的樹序列化（application 層不依賴 JSON 函式庫）。 */
final class JsonStrings {

    private JsonStrings() {
    }

    /**
     * 把 {@code Map／List／String／Number／Boolean／null} 組成的樹序列化成緊湊 JSON 文字（passCriteriaSpec 的落庫形式；
     * domain 只保存 JSON 文字、不解析）。其他型別以 {@code toString()} 當字串處理。
     */
    static String toJson(Object value) {
        StringBuilder out = new StringBuilder();
        write(out, value);
        return out.toString();
    }

    private static void write(StringBuilder out, Object value) {
        if (value == null) {
            out.append("null");
        } else if (value instanceof Map<?, ?> map) {
            out.append('{');
            boolean first = true;
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (!first) {
                    out.append(',');
                }
                first = false;
                out.append(quote(String.valueOf(entry.getKey()))).append(':');
                write(out, entry.getValue());
            }
            out.append('}');
        } else if (value instanceof Iterable<?> items) {
            out.append('[');
            boolean first = true;
            for (Object item : items) {
                if (!first) {
                    out.append(',');
                }
                first = false;
                write(out, item);
            }
            out.append(']');
        } else if (value instanceof Boolean || value instanceof Number) {
            out.append(value);
        } else {
            out.append(quote(value.toString()));
        }
    }

    /** 回傳含外層雙引號的 JSON 字串字面值：跳脫 {@code "}、{@code \}、控制字元與 U+2028／U+2029。 */
    static String quote(String value) {
        StringBuilder out = new StringBuilder(value.length() + 2).append('"');
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '"' -> out.append("\\\"");
                case '\\' -> out.append("\\\\");
                case '\n' -> out.append("\\n");
                case '\r' -> out.append("\\r");
                case '\t' -> out.append("\\t");
                case '\b' -> out.append("\\b");
                case '\f' -> out.append("\\f");
                default -> {
                    if (c < 0x20 || c == 0x2028 || c == 0x2029) {
                        out.append(String.format("\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
                }
            }
        }
        return out.append('"').toString();
    }
}
