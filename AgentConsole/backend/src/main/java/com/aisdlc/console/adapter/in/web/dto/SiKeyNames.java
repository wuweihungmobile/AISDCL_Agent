package com.aisdlc.console.adapter.in.web.dto;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * SelfImproving 回應的欄名對映（TCS-SelfImprovingMirror-P1b R9；AC-SI-32-1 所稱「snake_case↔camelCase 對映」的唯一定義，⚖ 2）。
 *
 * <p>{@link #camel}：鍵若符合 {@code ^[a-z][a-z0-9]*(_[a-z0-9]+)+$}，依 {@code _} 切段、首段不動、其後各段首字元轉大寫（數字不變）、
 * 串接（{@code http_status}→{@code httpStatus}、{@code touched_sha256}→{@code touchedSha256}）；<b>其餘鍵恆等</b>
 * （{@code digest8}、{@code PROP-SI-004}、{@code quota-band}、中文鍵、已含大寫的鍵、單字鍵、{@code a__b}、{@code _x}、{@code x_}）。
 * {@link #camelKeys}：套用在整棵樹<b>所有層級的所有物件鍵</b>；值（字串、數字、布林、{@code null}、陣列元素的個數與順序）一律不動——
 * {@code null} 保留（{@code head_sha}、{@code next_since}、{@code cooldown} 的 {@code null} 有語意）、{@code card} 字串逐位元組不動。
 *
 * <p>兩個不同的來源鍵轉出同一個名字（例：{@code x_1} 與本來就叫 {@code x1} 的鍵）時<b>不丟欄</b>：不變的鍵先保有它的名字，
 * 轉換後撞名者保留原鍵（來源鍵本身不重複、而原鍵含底線、轉換結果不含底線，所以保留原鍵不會再撞）。
 */
public final class SiKeyNames {

    private static final Pattern SNAKE = Pattern.compile("[a-z][a-z0-9]*(?:_[a-z0-9]+)+");

    private SiKeyNames() {
    }

    /** 單一鍵的對映；{@code null} 輸入丟 {@link NullPointerException}（鍵不會是 null，傳 null 是呼叫端的 bug，不回亂值）。 */
    public static String camel(String key) {
        Objects.requireNonNull(key, "key");
        if (!SNAKE.matcher(key).matches()) {
            return key;
        }
        String[] parts = key.split("_");
        StringBuilder out = new StringBuilder(parts[0]);
        for (int i = 1; i < parts.length; i++) {
            out.append(Character.toUpperCase(parts[i].charAt(0))).append(parts[i], 1, parts[i].length());
        }
        return out.toString();
    }

    /** 整棵樹（{@code Map}／{@code List}／純量）的深層鍵對映；回新樹、不改輸入、保留鍵序。 */
    public static Object camelKeys(Object value) {
        if (value instanceof Map<?, ?> map) {
            Set<String> unchanged = new HashSet<>();
            for (Object key : map.keySet()) {
                String original = String.valueOf(key);
                if (camel(original).equals(original)) {
                    unchanged.add(original);
                }
            }
            Map<String, Object> out = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                String original = String.valueOf(entry.getKey());
                String name = camel(original);
                if (!name.equals(original) && (unchanged.contains(name) || out.containsKey(name))) {
                    name = original;
                }
                out.put(name, camelKeys(entry.getValue()));
            }
            return out;
        }
        if (value instanceof List<?> list) {
            List<Object> out = new ArrayList<>(list.size());
            for (Object item : list) {
                out.add(camelKeys(item));
            }
            return out;
        }
        return value;
    }
}
