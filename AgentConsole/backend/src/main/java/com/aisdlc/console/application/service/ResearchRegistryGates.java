package com.aisdlc.console.application.service;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * 追蹤來源新增請求的輸入閘（API 契約 §5A.2；TCS-ResearchRegistry W-R5）：在 Bridge 之前先擋同一批形狀（零 Bridge 請求），違規一律 <b>400</b>，
 * 一次全列（{@code errors[]} 與 {@code details.violations[{field,rule,message}]}）。規則名與 Bridge 同名（{@code invalid_slug｜invalid_url｜invalid_kind｜
 * invalid_layer｜invalid_extract｜invalid_expand}），另加 {@code unknown_field}（含 {@code addedBy}：操作人一律取 JWT subject，請求本文不收，不被默默忽略）。
 *
 * <p>{@link #checkUrl} 是 Bridge {@code check_watch_url} 的原樣對應：<b>不做任何正規化</b>（大寫 host、顯式 {@code :443}、任何 IP 字面一律拒絕），
 * 判定逐列等於根層 TCS 附錄 D 的 CON 欄。Bridge 與 DB 的 CHECK 是第二、第三道；單一閘（host 須在有效網域清單）只有 Bridge 能判。
 */
public final class ResearchRegistryGates {

    public static final int URL_MAX = 500;
    public static final int EXTRACT_MAX = 200;
    public static final int PREFIX_MAX = 200;
    public static final List<String> KINDS = List.of("changelog", "docs", "release", "blog", "sitemap", "search");
    public static final List<String> LAYERS = List.of("ACADEMIC", "INDUSTRY", "OSS", "COMMUNITY");
    public static final List<String> EXPAND_MODES = List.of("links", "sitemap");

    private static final List<String> ALLOWED_FIELDS = List.of("slug", "url", "kind", "extract", "layer", "expand");
    private static final Pattern SLUG = Pattern.compile("[a-z0-9][a-z0-9-]{0,31}");
    private static final Pattern HOST = Pattern.compile("[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?");
    private static final Pattern IPV4_LITERAL = Pattern.compile("[0-9.]+");

    private ResearchRegistryGates() {
    }

    /**
     * 驗新增本文並轉成 Bridge 的 snake_case 本文（不含 {@code added_by}，由服務層加 JWT subject）。違規＝丟 {@code ValidationException}（400）。
     */
    public static Map<String, Object> watchSource(Map<String, Object> body) {
        ResearchInputGates.Check check = new ResearchInputGates.Check();
        Map<String, Object> source = body == null ? Map.of() : body;
        source.keySet().stream().filter(key -> !ALLOWED_FIELDS.contains(key)).sorted().forEach(key -> check.add(key, "unknown_field",
                "不收欄位 " + key + "（操作人一律取 JWT subject，請求本文不收 addedBy）"));
        Object slug = source.get("slug");
        if (!(slug instanceof String s) || !SLUG.matcher(s).matches()) {
            check.add("slug", "invalid_slug", "slug 須為 1～32 字的小寫英數與連字號，且以英數起頭");
        }
        Object url = source.get("url");
        if (checkUrl(url) != null) {
            check.add("url", "invalid_url", "url 須為 https、小寫 ASCII host、無埠與 userinfo 與 IP 字面與片段、不超過 " + URL_MAX + " 字元（不自動改寫，請自行修正後重送）");
        }
        if (!KINDS.contains(source.get("kind"))) {
            check.add("kind", "invalid_kind", "kind 須為 " + String.join("、", KINDS) + " 之一");
        }
        if (!LAYERS.contains(source.get("layer"))) {
            check.add("layer", "invalid_layer", "layer 須為 " + String.join("、", LAYERS) + " 之一");
        }
        Object extract = source.get("extract");
        if (!(extract instanceof String text) || text.isEmpty() || text.codePointCount(0, text.length()) > EXTRACT_MAX || hasControl(text)) {
            check.add("extract", "invalid_extract", "extract 須為 1～" + EXTRACT_MAX + " 字且不含控制字元");
        }
        Map<String, Object> expand = null;
        Object rawExpand = source.get("expand");
        if (rawExpand != null) {
            expand = expand(check, rawExpand);
        }
        if (!check.violations.isEmpty()) {
            throw check.validation();
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("slug", slug);
        out.put("url", url);
        out.put("kind", source.get("kind"));
        out.put("extract", extract);
        out.put("layer", source.get("layer"));
        if (expand != null) {
            out.put("expand", expand);
        }
        return out;
    }

    private static Map<String, Object> expand(ResearchInputGates.Check check, Object raw) {
        String message = "expand 須缺省（或 null），或為恰含 mode、prefix、max 的物件";
        if (!(raw instanceof Map<?, ?> map) || map.size() != 3 || !map.containsKey("mode") || !map.containsKey("prefix") || !map.containsKey("max")) {
            check.add("expand", "invalid_expand", message);
            return null;
        }
        Object mode = map.get("mode");
        Object prefix = map.get("prefix");
        Object max = map.get("max");
        if (!EXPAND_MODES.contains(mode)) {
            check.add("expand", "invalid_expand", "expand.mode 須為 " + String.join("、", EXPAND_MODES) + " 之一");
        } else if (!(prefix instanceof String p) || !p.startsWith("/") || p.length() > PREFIX_MAX || hasSpaceOrReserved(p)) {
            check.add("expand", "invalid_expand", "expand.prefix 須以 / 起頭、不超過 " + PREFIX_MAX + " 字元、不含空白與 ? # 與控制字元");
        } else if (!(max instanceof Integer || max instanceof Long || max instanceof Short) || ((Number) max).longValue() < 1 || ((Number) max).longValue() > 3) {
            check.add("expand", "invalid_expand", "expand.max 須為 1～3 的整數");
        } else {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("mode", mode);
            out.put("prefix", prefix);
            out.put("max", ((Number) max).intValue());
            return out;
        }
        return null;
    }

    /**
     * Bridge {@code check_watch_url} 的原樣對應：回 {@code null}＝接受，否則回 {@code "invalid_url"}。全 ASCII 且無空白與控制字元、無 {@code #}、{@code https://} 起頭、
     * 總長 ≤500；host（第一個 {@code /} 或 {@code ?} 之前）須合 {@code [a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?}；任一 label 為 {@code xn--} 開頭、{@code localhost} 與
     * {@code *.localhost}、IPv4 字面一律拒絕。
     */
    public static String checkUrl(Object url) {
        final String bad = "invalid_url";
        if (!(url instanceof String text) || text.length() > URL_MAX || !text.startsWith("https://")) {
            return bad;
        }
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (c <= 0x20 || c >= 0x7F || c == '#') {
                return bad;
            }
        }
        String rest = text.substring("https://".length());
        int slash = rest.indexOf('/');
        int query = rest.indexOf('?');
        int cut = slash < 0 ? (query < 0 ? rest.length() : query) : (query < 0 ? slash : Math.min(slash, query));
        String host = rest.substring(0, cut);
        if (!HOST.matcher(host).matches()) {
            return bad;
        }
        for (String label : host.split("\\.", -1)) {
            if (label.startsWith("xn--")) {
                return bad;
            }
        }
        if (host.equals("localhost") || host.endsWith(".localhost") || IPV4_LITERAL.matcher(host).matches()) {
            return bad;
        }
        return null;
    }

    private static boolean hasControl(String text) {
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (c < 0x20 || c == 0x7F) {
                return true;
            }
        }
        return false;
    }

    private static boolean hasSpaceOrReserved(String text) {
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (c <= 0x20 || c == 0x7F || c == '?' || c == '#') {
                return true;
            }
        }
        return false;
    }
}
