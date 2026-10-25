package com.aisdlc.console.application.service;

import java.util.List;

/**
 * 稽核 JSON 的緊湊寫法（TCS-SelfImprovingDecide-P2b W7）：鍵序由呼叫順序決定、無空白、無結尾換行、非 ASCII 字元原樣（不 {@code \}u 跳脫）、
 * 字串依標準 JSON 逸出（{@code "}、{@code \}、控制字元；{@code /} 不逸出）。
 *
 * <p>為什麼不交給 Jackson：稽核 body 是 HMAC 的對象，<b>位元組必須與根層 Python 的 {@code json.dumps(separators=(",", ":"),
 * ensure_ascii=False)} 逐位元組相同、且鍵序固定</b>；用一個明確寫出每個字元的小寫法器，比設定一個序列化器去逼近它更可證、更不會因升級而漂移。
 */
final class SiAuditJson {

    private final StringBuilder out = new StringBuilder("{");
    private boolean first = true;

    SiAuditJson string(String key, String value) {
        return raw(key, quote(value));
    }

    /** 值為 {@code null} 時寫 JSON {@code null}（鍵仍在）。 */
    SiAuditJson nullableString(String key, String value) {
        return raw(key, value == null ? "null" : quote(value));
    }

    SiAuditJson number(String key, long value) {
        return raw(key, Long.toString(value));
    }

    SiAuditJson bool(String key, boolean value) {
        return raw(key, value ? "true" : "false");
    }

    SiAuditJson stringArray(String key, List<String> values) {
        StringBuilder array = new StringBuilder("[");
        for (int i = 0; i < values.size(); i++) {
            if (i > 0) {
                array.append(',');
            }
            array.append(quote(values.get(i)));
        }
        return raw(key, array.append(']').toString());
    }

    String end() {
        return out.append('}').toString();
    }

    private SiAuditJson raw(String key, String json) {
        if (!first) {
            out.append(',');
        }
        first = false;
        out.append(quote(key)).append(':').append(json);
        return this;
    }

    /** JSON 字串字面值（含兩側引號）。 */
    static String quote(String value) {
        StringBuilder sb = new StringBuilder(value.length() + 2).append('"');
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '"' -> sb.append("\\\"");
                case '\\' -> sb.append("\\\\");
                case '\b' -> sb.append("\\b");
                case '\f' -> sb.append("\\f");
                case '\n' -> sb.append("\\n");
                case '\r' -> sb.append("\\r");
                case '\t' -> sb.append("\\t");
                default -> {
                    if (c < 0x20) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
                }
            }
        }
        return sb.append('"').toString();
    }
}
