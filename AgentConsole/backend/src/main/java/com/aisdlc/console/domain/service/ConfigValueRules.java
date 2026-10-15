package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.config.ConfigSpec;
import com.aisdlc.console.domain.model.config.ConfigValueType;
import com.aisdlc.console.domain.model.config.SystemConfig;

import java.math.BigDecimal;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

/**
 * 設定值的型別、{@code validation_rule}、範圍與選項校驗（契約 §1.5.3 驗證順序的第 2 項）。純 Java。
 *
 * <p>通則（契約 §1.5）：{@code value} 一律是字串——INTEGER／LONG＝{@code ^(0|-?[1-9][0-9]*)$}；
 * FLOAT＝{@code ^-?[0-9]+(\.[0-9]+)?$}；BOOLEAN＝小寫 {@code true}／{@code false}；ENUM＝選項之一（區分大小寫）；
 * STRING＝不含 NUL、≤ 4,000 字元；ENCRYPTED＝非空 ≤ 512 字元，或空字串表示清除。
 * 通過型別後再套 {@code validation_rule}（Java 正規表示式、對完整字串比對），最後比數值範圍。
 */
public final class ConfigValueRules {

    public static final int MAX_VALUE_LENGTH = 4000;
    public static final int MAX_ENCRYPTED_LENGTH = 512;

    private static final Pattern INTEGER = Pattern.compile("^(0|-?[1-9][0-9]*)$");
    private static final Pattern FLOAT = Pattern.compile("^-?[0-9]+(\\.[0-9]+)?$");
    private static final Map<String, Pattern> COMPILED = new ConcurrentHashMap<>();

    private ConfigValueRules() {
    }

    /** 校驗失敗的人話訊息（放進 {@code errors[0].message}）。 */
    public record Failure(String message) {
    }

    /** @return 失敗原因；通過回 empty */
    public static Optional<Failure> check(SystemConfig config, ConfigSpec spec, String value) {
        if (value == null) {
            return fail("值不可為空（null）");
        }
        ConfigValueType type = config.valueType();
        if (type == ConfigValueType.ENCRYPTED) {
            if (value.length() > MAX_ENCRYPTED_LENGTH) {
                return fail("長度不可超過 " + MAX_ENCRYPTED_LENGTH + " 字元");
            }
        } else if (value.length() > MAX_VALUE_LENGTH) {
            return fail("長度不可超過 " + MAX_VALUE_LENGTH + " 字元");
        }
        if (value.indexOf('\0') >= 0) {
            return fail("不可包含 NUL 字元");
        }
        switch (type) {
            case INTEGER, LONG -> {
                if (!INTEGER.matcher(value).matches()) {
                    return fail(rangeHint("需為整數", spec));
                }
            }
            case FLOAT -> {
                if (!FLOAT.matcher(value).matches()) {
                    return fail(rangeHint("需為數字", spec));
                }
            }
            case BOOLEAN -> {
                if (!value.equals("true") && !value.equals("false")) {
                    return fail("需為 true 或 false（小寫）");
                }
            }
            case ENUM -> {
                if (spec != null && !spec.options().contains(value)) {
                    return fail("需為下列之一：" + String.join("、", spec.options()));
                }
            }
            default -> {
                // STRING、ENCRYPTED：長度與 NUL 已檢查
            }
        }
        String rule = config.validationRule();
        if (rule != null && !rule.isEmpty() && !pattern(rule).matcher(value).matches()) {
            return fail(type == ConfigValueType.INTEGER || type == ConfigValueType.LONG
                    || type == ConfigValueType.FLOAT ? rangeHint(type == ConfigValueType.FLOAT ? "需為數字" : "需為整數", spec)
                    : "格式不符：" + rule);
        }
        if (spec != null && isNumeric(type)) {
            BigDecimal number = new BigDecimal(value);
            if ((spec.min() != null && number.compareTo(spec.min()) < 0)
                    || (spec.max() != null && number.compareTo(spec.max()) > 0)) {
                return fail(rangeHint(type == ConfigValueType.FLOAT ? "需為數字" : "需為整數", spec));
            }
        }
        return Optional.empty();
    }

    private static boolean isNumeric(ConfigValueType type) {
        return type == ConfigValueType.INTEGER || type == ConfigValueType.LONG || type == ConfigValueType.FLOAT;
    }

    /** 例：{@code 需為整數（1～10）}；沒有範圍就只有前綴。 */
    private static String rangeHint(String prefix, ConfigSpec spec) {
        if (spec == null || (spec.min() == null && spec.max() == null)) {
            return prefix;
        }
        String min = spec.min() == null ? "" : spec.min().stripTrailingZeros().toPlainString();
        String max = spec.max() == null ? "" : spec.max().stripTrailingZeros().toPlainString();
        return prefix + "（" + min + "～" + max + "）";
    }

    private static Optional<Failure> fail(String message) {
        return Optional.of(new Failure(message));
    }

    private static Pattern pattern(String rule) {
        try {
            return COMPILED.computeIfAbsent(rule, Pattern::compile);
        } catch (PatternSyntaxException e) {
            throw new IllegalStateException("system_configs.validation_rule 不是合法的正規表示式：" + rule, e);
        }
    }
}
