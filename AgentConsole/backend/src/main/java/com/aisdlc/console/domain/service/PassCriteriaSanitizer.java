package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violation;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

/**
 * NFR-SEC-03 第 1 層：UI 輸入 → 引擎指令的消毒（Architecture §8.3）。
 *
 * <p>🔴 黑名單字元集 SSOT＝{@code AutoClaude/autoclaude/utils/shell_deny_chars.py} 的
 * {@code BASE_DENY_CHARS = frozenset("!`><~$&;")}（8 個字元，與 {@code SddToPlaybookAdapter} 同一組）。
 * 本檔複製該常數（後端不能 import Python）；兩者一致性由 W4 QA 以腳本比對，
 * 並由 PassCriteriaSanitizerTest 以字面值釘住——任何一邊改動都必須同步另一邊。
 *
 * <p>除黑名單字元外，另拒絕換行等控制字元：evaluatorCommand 是單行命令，換行在 shell 內等同命令分隔，
 * 屬同一類注入手法（比 SSOT 更嚴，不影響字元集一致性）。
 */
public final class PassCriteriaSanitizer {

    /** SSOT 的 8 個黑名單字元，依 SSOT 字面順序。 */
    public static final Set<Character> DENY_CHARS = Collections.unmodifiableSet(
            new LinkedHashSet<>(List.of('!', '`', '>', '<', '~', '$', '&', ';')));

    private PassCriteriaSanitizer() {
    }

    /** 命令中出現的黑名單字元（去重、依首次出現順序）。 */
    public static List<Character> violationsOf(String command) {
        Set<Character> found = new LinkedHashSet<>();
        if (command != null) {
            for (char c : command.toCharArray()) {
                if (DENY_CHARS.contains(c)) {
                    found.add(c);
                }
            }
        }
        return List.copyOf(found);
    }

    /**
     * 命令必須不含黑名單字元與控制字元，否則丟 {@link ValidationException}（400）並列出違規字元。
     * null 或空白視為「未提供」，直接放行（由呼叫端決定是否必填）。
     */
    public static void requireSafeCommand(String field, String command) {
        if (command == null || command.isBlank()) {
            return;
        }
        List<Violation> violations = new ArrayList<>();
        List<String> shown = new ArrayList<>();
        List<Character> denied = violationsOf(command);
        if (!denied.isEmpty()) {
            denied.forEach(c -> shown.add(String.valueOf(c)));
            violations.add(new Violation(field, field + " 含禁用字元：" + String.join(" ", shown)));
        }
        if (command.chars().anyMatch(Character::isISOControl)) {
            violations.add(new Violation(field, field + " 不可包含換行或其他控制字元"));
        }
        if (!violations.isEmpty()) {
            throw new ValidationException(violations.get(0).message(), "命令含禁用字元",
                    violations, Map.of("violations", shown));
        }
    }

    /** 正規表示式必須能 {@link Pattern#compile(String)}，否則丟 {@link ValidationException}（400）。 */
    public static void requireCompilableRegex(String field, String regex) {
        if (regex == null || regex.isBlank()) {
            return;
        }
        try {
            Pattern.compile(regex);
        } catch (PatternSyntaxException e) {
            throw ValidationException.of(field,
                    field + " 不是合法的正規表示式：" + e.getDescription() + "（位置 " + e.getIndex() + "）");
        }
    }
}
