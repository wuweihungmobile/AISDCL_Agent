package com.aisdlc.console.adapter.out.persistence.research;

import java.util.List;
import java.util.regex.Pattern;

/**
 * 自癒歷史 excerpt 的遮蔽器（AC-R2P-16-4；D-138 Q-6）。<b>先遮蔽、再取尾端 300 字元</b>（以 Unicode code point 計，補充平面字元不會被切半），
 * 恆遮、不讀任何開關。規則逐一對應 Bridge 端 {@code healing.py::mask}：先 {@code AutoClaude/autoclaude/utils/redaction.py::redact_secrets}
 * （日誌補充樣式 → DSN 密碼段 → 既有敏感樣式），後 {@code gitops.py::redact} 的 GitHub token 樣式。兩端各自實作，唯一的機械鎖是共用夾具
 * {@code engine-bridge/tests/fixtures/research/healing_redaction_cases.json}（pytest 與 {@code HealingExcerptMaskerTest} 同讀）。
 */
final class HealingExcerptMasker {

    /** excerpt 上限（字元，非 UTF-16 code unit）。 */
    static final int EXCERPT_CHARS = 300;
    private static final String REDACTED = "[REDACTED]";
    private static final String MASK = "***";

    private static final String VALUE = "(?:\\[REDACTED\\]|\"[^\"]*\"|'[^']*'|\\S+)";
    private static final String KEY_START = "(?<![A-Za-z0-9])";
    private static final String ASSIGN = "[\"']?\\s*[=:]\\s*";

    private static final List<Pattern> KEEP_KEY_PATTERNS = List.of(
            Pattern.compile("(?i)(" + KEY_START + "AUTOCLAUDE_(?:DB|PG)_DSN" + ASSIGN + ")" + VALUE),
            Pattern.compile("(?i)(" + KEY_START + "(?:password|passwd|secret|api[_-]?key|(?:access|auth|refresh)[_-]?token)" + ASSIGN + ")" + VALUE),
            Pattern.compile("(?i)(" + KEY_START + "authorization\\s*:\\s*)(?:(?:bearer|basic|digest|token|negotiate)\\s+)?" + VALUE));
    private static final Pattern SK_ANT = Pattern.compile("sk-ant-[A-Za-z0-9\\-_]+");
    private static final Pattern DSN_PASSWORD = Pattern.compile("(://[^:/@]+:)([^@]+)(@)");
    private static final List<Pattern> SENSITIVE = List.of(
            Pattern.compile("(?i)(bearer\\s+)[A-Za-z0-9\\-._~+/]+=*"),
            Pattern.compile("sk-[A-Za-z0-9\\-_]{20,}"),
            Pattern.compile("(?i)authorization:\\s*\\S+"));
    private static final List<Pattern> TOKENS = List.of(
            Pattern.compile("gh[pousr]_[A-Za-z0-9_]{16,}"),
            Pattern.compile("github_pat_[A-Za-z0-9_]{16,}"));

    private HealingExcerptMasker() {
    }

    /** 遮蔽（不截尾）；空值回空字串。 */
    static String mask(String text) {
        if (text == null || text.isEmpty()) {
            return "";
        }
        String out = text;
        for (Pattern pattern : KEEP_KEY_PATTERNS) {
            out = pattern.matcher(out).replaceAll("$1" + REDACTED);
        }
        out = SK_ANT.matcher(out).replaceAll(REDACTED);
        out = DSN_PASSWORD.matcher(out).replaceAll("$1***$3");
        for (Pattern pattern : SENSITIVE) {
            out = pattern.matcher(out).replaceAll(REDACTED);
        }
        for (Pattern pattern : TOKENS) {
            out = pattern.matcher(out).replaceAll(MASK);
        }
        return out;
    }

    /** 先遮蔽、再取尾端 {@link #EXCERPT_CHARS} 個字元（code point）。 */
    static String excerpt(String text) {
        String masked = mask(text);
        int count = masked.codePointCount(0, masked.length());
        if (count <= EXCERPT_CHARS) {
            return masked;
        }
        return masked.substring(masked.offsetByCodePoints(0, count - EXCERPT_CHARS));
    }
}
