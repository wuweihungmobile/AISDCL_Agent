package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.AllowlistInput;
import com.aisdlc.console.application.port.in.ResearchCommandUseCase.ApproveInput;
import com.aisdlc.console.application.port.in.ResearchCommandUseCase.CreateInput;
import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Layers;
import com.aisdlc.console.application.port.in.ResearchCommandUseCase.ReinitInput;
import com.aisdlc.console.application.port.in.ResearchCommandUseCase.SavePrdInput;
import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Scope;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violation;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Supplier;
import java.util.regex.Pattern;

/**
 * 研究寫入請求的輸入閘（API 契約 §1.2；Architecture §8.3 第 1 層）。每個閘<b>一次回報全部違規</b>，違規一律帶 {@code field}、{@code rule}、{@code message}：
 * {@code errors[]}（欄位與說明，沿用共通封包）與 {@code details.violations[{field,rule,message}]}（多一個 {@code rule}，共通封包的 {@code errors[]} 項沒有這個欄位）。
 * 建立端點違規回 <b>400</b>（契約 §0.2 第 5 列：console-api 欄位級 {@code errors[]}），其餘寫入端點回 <b>422</b>（先例 {@code SiWriteGates}）；頂層 reason 為
 * {@value #INVALID_REQUEST}，只有「產業層需要 Web 層、而 Web 層未啟用」這一類違規單獨出現時才是 {@code layer_unavailable}。
 *
 * <p>閘的目的是<b>不把明知會被拒的請求送到 Bridge</b>（零 Bridge 請求）：Bridge 另有自己的一份檢查（防禦縱深），兩者的規則以契約 §1.2 為準；Bridge 專屬的規則
 * （{@code in_scope} 至少一項、軸標籤取自登錄表、expectedDigests 須涵蓋四個檔）不在這裡複製。
 */
public final class ResearchInputGates {

    /** 入口閘的頂層 {@code reason}（與 Bridge 層同名同義；以區域常數持有、不進 {@code ErrorReasons}，先例 {@code SiWriteGates}）。 */
    public static final String INVALID_REQUEST = "invalid_request";

    public static final int TITLE_MAX = 200;
    public static final int TOPIC_MAX = 500;
    public static final int TECH_STACK_MAX = 200;
    public static final int SCOPE_LIST_MAX_ITEMS = 20;
    public static final int SCOPE_ITEM_MAX = 200;
    public static final int AXES_MAX_ITEMS = 6;
    public static final int AXIS_MAX = 40;
    public static final int REASON_MAX = 500;
    public static final int CHANGE_SUMMARY_MAX = 500;
    public static final int PURPOSE_MAX = 200;
    /** PRD 內容上限：1 MiB（UTF-8 位元組；契約 §1.2）。 */
    public static final int PRD_MAX_BYTES = 1_048_576;
    public static final int MIN_INTERVAL_MIN = 1;
    public static final int MIN_INTERVAL_MAX = 3600;

    public static final List<String> DEPTH_LEVELS = List.of("QUICK", "STANDARD", "DEEP");
    public static final List<String> TARGET_SCOPE_HINTS = List.of("AISDLC_MODULE", "STANDALONE_PROJECT", "UNDECIDED");
    public static final List<String> STAGES = List.of("research", "draft", "review", "revise", "iterate", "tcs-draft");
    public static final List<String> LIST_KINDS = List.of("FETCH", "WEB");
    public static final List<String> LAYERS = List.of("ACADEMIC", "INDUSTRY", "OSS", "COMMUNITY");

    private static final Pattern SLUG = Pattern.compile("[a-z0-9][a-z0-9-]{0,29}");
    private static final Pattern HOST = Pattern.compile("[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?");
    private static final Pattern REDDIT = Pattern.compile("(^|\\.)(reddit\\.com|redd\\.it)$");
    private static final Pattern DIGEST = Pattern.compile("sha256:[0-9a-f]{64}");

    private ResearchInputGates() {
    }

    /** 建立請求通過閘後要送給 Bridge 的欄位（{@code scope} 已是 Bridge 的 snake_case 形狀，只含請求有給的鍵）。 */
    public record CreateBody(String slug, String title, String topic, Map<String, Object> scope, String depthLevel) {
    }

    // ── 建立專案（API-RP-03）──────────────────────────────────────────────────────────────

    /**
     * 驗建立請求。{@code webLayerEnabled} 只在 {@code industry} 為真時才呼叫（探針可能要打一次 Bridge；快取 30 秒）；回 empty＝量不到（Bridge 不可達等），
     * 這時不擋，由 Bridge 入口自己判（契約：產業層需要 Web 層）。
     */
    public static CreateBody create(CreateInput input, Supplier<Optional<Boolean>> webLayerEnabled) {
        Check check = new Check();
        String slug = input.slug();
        if (slug == null) {
            check.add("slug", "required", "slug 為必填");
        } else if (!SLUG.matcher(slug).matches()) {
            check.add("slug", "pattern", "slug 須為 1～30 字的小寫英數與連字號，且以英數起頭");
        }
        String title = requiredText(check, "title", input.title(), TITLE_MAX);
        String topic = requiredText(check, "topic", input.topic(), TOPIC_MAX);
        String depth = input.depthLevel() == null ? "STANDARD" : input.depthLevel();
        if (!DEPTH_LEVELS.contains(depth)) {
            check.add("depthLevel", "invalid_value", "depthLevel 須為 " + String.join("、", DEPTH_LEVELS) + " 之一");
        }
        if (input.targetScopeHint() != null && !TARGET_SCOPE_HINTS.contains(input.targetScopeHint())) {
            check.add("targetScopeHint", "invalid_value", "targetScopeHint 須為 " + String.join("、", TARGET_SCOPE_HINTS) + " 之一");
        }
        Map<String, Object> scope = new LinkedHashMap<>();
        if (input.scope() == null) {
            check.add("scope", "required", "scope 為必填");
        } else {
            scope = scope(check, input.scope(), webLayerEnabled);
        }
        if (input.targetScopeHint() != null && TARGET_SCOPE_HINTS.contains(input.targetScopeHint())) {
            scope.put("target_scope_hint", input.targetScopeHint());
        }
        if (!check.violations.isEmpty()) {
            throw check.validation();
        }
        return new CreateBody(slug, title, topic, scope, depth);
    }

    private static Map<String, Object> scope(Check check, Scope scope, Supplier<Optional<Boolean>> webLayerEnabled) {
        Map<String, Object> out = new LinkedHashMap<>();
        Layers layers = scope.layers();
        if (layers == null) {
            check.add("scope.layers", "required", "scope.layers 為必填（academic、industry、oss、community 四個布林）");
        } else {
            Map<String, Boolean> flags = new LinkedHashMap<>();
            flags.put("academic", layers.academic());
            flags.put("industry", layers.industry());
            flags.put("oss", layers.oss());
            flags.put("community", layers.community());
            Map<String, Object> bridgeLayers = new LinkedHashMap<>();
            flags.forEach((name, value) -> {
                if (value == null) {
                    check.add("scope.layers." + name, "required", "scope.layers." + name + " 為必填（布林）");
                } else {
                    bridgeLayers.put(name, value);
                }
            });
            if (bridgeLayers.size() == flags.size() && !bridgeLayers.containsValue(Boolean.TRUE)) {
                check.add("scope.layers", "at_least_one", "四個層開關至少一個須為 true");
            }
            if (Boolean.TRUE.equals(layers.industry()) && Boolean.FALSE.equals(webLayerEnabled.get().orElse(null))) {
                check.add("scope.layers.industry", Check.WEB_LAYER_RULE, "產業層需要 Web 層，但 Bridge 的 Web 層未啟用（BRIDGE_RESEARCH_WEB_ALLOWLIST 為空）");
            }
            out.put("layers", bridgeLayers);
        }
        if (scope.techStack() != null) {
            if (scope.techStack().codePointCount(0, scope.techStack().length()) > TECH_STACK_MAX) {
                check.add("scope.techStack", "max_length", "techStack 不可超過 " + TECH_STACK_MAX + " 字");
            } else if (scope.techStack().indexOf('\0') >= 0) {
                check.add("scope.techStack", "invalid_char", "techStack 不可含 NUL 字元");
            } else {
                out.put("tech_stack", scope.techStack());
            }
        }
        putList(check, out, "in_scope", "scope.inScope", scope.inScope(), 0, SCOPE_LIST_MAX_ITEMS, SCOPE_ITEM_MAX);
        putList(check, out, "out_of_scope", "scope.outOfScope", scope.outOfScope(), 0, SCOPE_LIST_MAX_ITEMS, SCOPE_ITEM_MAX);
        if (scope.recencyYears() != null) {
            if (scope.recencyYears() < 1 || scope.recencyYears() > 3) {
                check.add("scope.recencyYears", "invalid_value", "recencyYears 須為 1、2 或 3");
            } else {
                out.put("recency_years", scope.recencyYears());
            }
        }
        putList(check, out, "applicability_axes", "scope.applicabilityAxes", scope.applicabilityAxes(), 1, AXES_MAX_ITEMS, AXIS_MAX);
        return out;
    }

    private static void putList(Check check, Map<String, Object> out, String bridgeKey, String field, List<String> items, int minItems,
                                int maxItems, int itemMax) {
        if (items == null) {
            return;
        }
        boolean ok = true;
        if (items.size() < minItems) {
            check.add(field, "min_items", field + " 至少 " + minItems + " 項");
            ok = false;
        }
        if (items.size() > maxItems) {
            check.add(field, "max_items", field + " 最多 " + maxItems + " 項");
            ok = false;
        }
        for (int i = 0; i < items.size(); i++) {
            String item = items.get(i);
            if (item == null || item.isBlank()) {
                check.add(field + "[" + i + "]", "invalid_value", field + "[" + i + "] 不可為空白");
                ok = false;
            } else if (item.codePointCount(0, item.length()) > itemMax) {
                check.add(field + "[" + i + "]", "max_length", field + "[" + i + "] 不可超過 " + itemMax + " 字");
                ok = false;
            } else if (item.indexOf('\0') >= 0) {
                check.add(field + "[" + i + "]", "invalid_char", field + "[" + i + "] 不可含 NUL 字元");
                ok = false;
            }
        }
        if (ok) {
            out.put(bridgeKey, List.copyOf(items));
        }
    }

    // ── 存 PRD 新版（API-RP-09）──────────────────────────────────────────────────────────────

    /** 驗存檔請求；通過回去前後空白的 {@code changeSummary}（沒給＝空字串）。 */
    public static String savePrd(SavePrdInput input) {
        Check check = new Check();
        if (input.baseVersion() == null) {
            check.add("baseVersion", "required", "baseVersion 為必填（目前 head 的版號；尚無版本為 0）");
        } else if (input.baseVersion() < 0) {
            check.add("baseVersion", "invalid_value", "baseVersion 不可為負數");
        }
        String content = input.content();
        if (content == null || content.isBlank()) {
            check.add("content", "required", "content 為必填，不可全為空白");
        } else if (content.indexOf('\0') >= 0) {
            check.add("content", "invalid_content", "content 不可含 NUL 字元");
        } else if (content.getBytes(StandardCharsets.UTF_8).length > PRD_MAX_BYTES) {
            check.add("content", "too_large", "content 不可超過 1 MiB（UTF-8 位元組）");
        }
        String summary = input.changeSummary() == null ? "" : input.changeSummary().strip();
        if (summary.codePointCount(0, summary.length()) > CHANGE_SUMMARY_MAX) {
            check.add("changeSummary", "max_length", "changeSummary 不可超過 " + CHANGE_SUMMARY_MAX + " 字");
        }
        check.throwIfAny();
        return summary;
    }

    // ── Gate 0 核准／退回（API-RP-12、API-RP-21）──────────────────────────────────────────────

    /** 驗核准請求；通過回去前後空白的 {@code reason}（沒給＝null）。 */
    public static String approve(ApproveInput input) {
        Check check = new Check();
        if (input.prdVersion() == null) {
            check.add("prdVersion", "required", "prdVersion 為必填（整數版號 versionNo）");
        } else if (input.prdVersion() < 1) {
            check.add("prdVersion", "invalid_value", "prdVersion 須為 1 以上的整數");
        }
        Map<String, String> digests = input.expectedDigests();
        if (digests == null || digests.isEmpty()) {
            check.add("expectedDigests", "required", "expectedDigests 為必填（相對 POSIX 路徑 → sha256:<64 位小寫十六進位>）");
        } else {
            digests.forEach((path, digest) -> {
                String field = "expectedDigests." + path;
                if (!relativePosix(path)) {
                    check.add("expectedDigests", "invalid_path", "鍵 " + path + " 須為相對 POSIX 路徑（不以 / 起頭、不含 \\ 與 .. 段）");
                }
                if (digest == null || !DIGEST.matcher(digest).matches()) {
                    check.add(field, "invalid_digest", "值須為 sha256: 加 64 位小寫十六進位");
                }
            });
        }
        String reason = null;
        if (input.reason() != null) {
            reason = input.reason().strip();
            if (reason.isEmpty() || reason.codePointCount(0, reason.length()) > REASON_MAX) {
                check.add("reason", "invalid_length", "reason 須為 1～" + REASON_MAX + " 字（沒有理由就不要帶這個欄位）");
            }
        }
        check.throwIfAny();
        return reason;
    }

    /** 驗必填的理由（退回修改、換世代）；通過回去前後空白的理由。 */
    public static String requiredReason(String raw) {
        Check check = new Check();
        String reason = raw == null ? "" : raw.strip();
        if (reason.isEmpty()) {
            check.add("reason", "required", "reason 為必填，不可全為空白");
        } else if (reason.codePointCount(0, reason.length()) > REASON_MAX) {
            check.add("reason", "invalid_length", "reason 須為 1～" + REASON_MAX + " 字");
        }
        check.throwIfAny();
        return reason;
    }

    // ── 啟動階段（API-RP-11）、重試初始化／換世代（API-RP-20）───────────────────────────────

    public static void stage(String stage) {
        if (stage == null || !STAGES.contains(stage)) {
            Check check = new Check();
            check.add("stage", "invalid_value", "stage 須為 " + String.join("｜", STAGES) + " 之一");
            check.throwIfAny();
        }
    }

    /** 驗 reinit 本文：{@code generation} 只准缺省或 {@code next}；{@code next} 時 {@code reason} 必填。回要送給 Bridge 的理由（重試初始化＝null）。 */
    public static String reinit(ReinitInput input) {
        if (input.generation() == null) {
            return null;
        }
        if (!"next".equals(input.generation())) {
            Check check = new Check();
            check.add("generation", "invalid_value", "generation 只准 next（缺省＝重試初始化）");
            check.throwIfAny();
        }
        return requiredReason(input.reason());
    }

    // ── allowlist（API-RP-22）──────────────────────────────────────────────────────────────

    /** 驗新增條目；Reddit 網域未確認條款回 422 {@code terms_ack_required}（其餘違規回 422 {@code invalid_request}）。 */
    public static void allowlistEntry(AllowlistInput input) {
        Check check = new Check();
        if (input.listKind() == null || !LIST_KINDS.contains(input.listKind())) {
            check.add("listKind", "invalid_value", "listKind 須為 " + String.join("、", LIST_KINDS) + " 之一");
        }
        String host = input.host();
        if (host == null || !HOST.matcher(host).matches()) {
            check.add("host", "invalid_host", "host 須為小寫主機名（無 scheme、埠、路徑與 userinfo；[a-z0-9.-]，英數起訖，≤253 字）");
        }
        if (input.layer() == null || !LAYERS.contains(input.layer())) {
            check.add("layer", "invalid_value", "layer 須為 " + String.join("、", LAYERS) + " 之一");
        }
        if (input.purpose() != null && input.purpose().codePointCount(0, input.purpose().length()) > PURPOSE_MAX) {
            check.add("purpose", "max_length", "purpose 不可超過 " + PURPOSE_MAX + " 字");
        }
        Integer interval = input.minIntervalSeconds();
        if (interval != null && (interval < MIN_INTERVAL_MIN || interval > MIN_INTERVAL_MAX)) {
            check.add("minIntervalSeconds", "out_of_range", "minIntervalSeconds 須為 " + MIN_INTERVAL_MIN + "～" + MIN_INTERVAL_MAX);
        }
        if (check.violations.isEmpty() && REDDIT.matcher(host).find() && !Boolean.TRUE.equals(input.tosAcknowledged())) {
            throw new UnprocessableException("Reddit 網域須先確認服務條款（tosAcknowledged 須為 true）", ErrorReasons.RESEARCH_TERMS_ACK_REQUIRED,
                    List.of(), List.of(new Violation("tosAcknowledged", "Reddit 網域須先確認服務條款")),
                    Map.of("violations", List.of(item("tosAcknowledged", "terms_ack_required", "Reddit 網域須先確認服務條款"))));
        }
        check.throwIfAny();
    }

    /** 驗停用／啟用本文：只准 {@code enabled}（布林）一鍵，其餘鍵＝422（條目不變）。回 enabled。 */
    public static boolean allowlistPatch(Map<String, Object> body) {
        Check check = new Check();
        Object enabled = body == null ? null : body.get("enabled");
        if (!(enabled instanceof Boolean)) {
            check.add("enabled", enabled == null ? "required" : "invalid_type", "enabled 為必填，且須為布林");
        }
        if (body != null) {
            body.keySet().stream().filter(key -> !"enabled".equals(key)).sorted().forEach(key -> check.add(key, "immutable",
                    "PATCH 只准改 enabled；" + key + " 建立後不可改（要調整＝停用該條目後重建）"));
        }
        check.throwIfAny();
        return (Boolean) enabled;
    }

    // ── 共用 ────────────────────────────────────────────────────────────────────────────────

    private static String requiredText(Check check, String field, String raw, int maxCodePoints) {
        if (raw == null || raw.isBlank()) {
            check.add(field, "required", field + " 為必填，不可全為空白");
            return null;
        }
        String value = raw.strip();
        if (value.indexOf('\0') >= 0) {
            check.add(field, "invalid_char", field + " 不可含 NUL 字元");
            return null;
        }
        int length = value.codePointCount(0, value.length());
        if (length > maxCodePoints) {
            check.add(field, "max_length", field + " 為 " + length + " 字，超過上限 " + maxCodePoints);
            return null;
        }
        return value;
    }

    private static boolean relativePosix(String path) {
        if (path == null || path.isBlank() || path.startsWith("/") || path.indexOf('\\') >= 0 || path.indexOf('\0') >= 0) {
            return false;
        }
        for (String segment : path.split("/", -1)) {
            if (segment.isEmpty() || "..".equals(segment)) {
                return false;
            }
        }
        return true;
    }

    private static Map<String, Object> item(String field, String rule, String message) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("field", field);
        out.put("rule", rule);
        out.put("message", message);
        return out;
    }

    /** 收集違規、一次丟出。 */
    private static final class Check {

        static final String WEB_LAYER_RULE = "web_layer_disabled";

        final List<Violation> violations = new ArrayList<>();
        private final List<Map<String, Object>> items = new ArrayList<>();
        private final List<String> rules = new ArrayList<>();

        void add(String field, String rule, String message) {
            violations.add(new Violation(field, message));
            items.add(item(field, rule, message));
            rules.add(rule);
        }

        void throwIfAny() {
            if (!violations.isEmpty()) {
                throw unprocessable();
            }
        }

        UnprocessableException unprocessable() {
            return new UnprocessableException("請求欄位未通過檢查（" + violations.size() + " 項）", INVALID_REQUEST, List.of(), violations,
                    Map.of("violations", items));
        }

        /** 建立端點：400。全部違規都是「Web 層未啟用」＝{@code layer_unavailable}，否則 {@code invalid_request}。 */
        ValidationException validation() {
            String reason = rules.stream().allMatch(WEB_LAYER_RULE::equals) ? ErrorReasons.RESEARCH_LAYER_UNAVAILABLE : INVALID_REQUEST;
            return new ValidationException("請求欄位未通過檢查（" + violations.size() + " 項）", reason, violations, Map.of("violations", items));
        }
    }
}
