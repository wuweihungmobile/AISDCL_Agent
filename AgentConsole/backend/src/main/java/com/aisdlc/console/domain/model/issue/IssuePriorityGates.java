package com.aisdlc.console.domain.model.issue;

import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.Violation;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * 優先順序請求的輸入閘（TCS-IssueCenter-20261027 R-IC-54、R-IC-55、R-IC-56、B-17；PRD §6.4）。<b>一次判完、一次全列</b>：違規一律 422、頂層 reason
 * 為 {@value #INVALID_REQUEST}、{@code details.violations[{field,message}]}（camelCase 欄名；{@code errors[]} 與它互為鏡像）。
 *
 * <p>為什麼不用具型別的請求物件與 Bean Validation：{@code rank} 為字串、小數、布林、陣列、物件、{@code null}、缺鍵都必須是 422（<b>不是 400</b>，
 * 更不能當成「清除」），框架綁定在型別不符時會先回 400；{@code note} 的 {@code null}（422）與缺鍵（＝空字串）也分不出來。所以控制器以 {@code Map} 收本文、
 * 型別與值域全由這裡判；只有「本文根本不是 JSON 物件」才由框架回 400。
 *
 * <p>規則：{@code id} 須符三種議題編號之一（與資料庫的 CHECK 同式）；{@code rank} 必填、整數、1～9999；{@code note} 選填（缺鍵＝空字串）、
 * 字串、至多 200 個字元（code point；全形與表情符號各算 1）、不含 U+0000～U+001F 與 U+007F（含首尾的換行，不靜默剝除）、不含孤立的代理字元
 * （會讓資料庫的 UTF-8 編碼失敗而回 500）。備註不去前後空白、原樣存入。
 */
public final class IssuePriorityGates {

    /** 本閘的頂層 {@code reason}（與 Bridge 層及 {@code SiWriteGates} 同名同義；不進 {@code ErrorReasons}）。 */
    public static final String INVALID_REQUEST = "invalid_request";

    public static final int RANK_MIN = 1;
    public static final int RANK_MAX = 9999;
    public static final int NOTE_MAX = 200;

    /** 與 {@code V14__issue_priority.sql} 的 CHECK 同式（ASCII 數字、整串比對）。 */
    private static final Pattern ISSUE_ID = Pattern.compile("(?:OBS-SI-[0-9]{3,}|PROP-SI-[0-9]{3,}|DEF-[0-9]+-[0-9]+)");
    private static final BigInteger BIG_MIN = BigInteger.valueOf(RANK_MIN);
    private static final BigInteger BIG_MAX = BigInteger.valueOf(RANK_MAX);

    private IssuePriorityGates() {
    }

    /** 通過的 PUT 輸入。 */
    public record Command(String id, int rank, String note) {
    }

    /** DELETE 的輸入閘：只驗 {@code id} 格式；違規丟 {@link UnprocessableException}。 */
    public static void checkId(String id) {
        Check check = new Check();
        id(check, id);
        check.throwIfAny();
    }

    /**
     * PUT 的輸入閘：{@code id} 與本文一次判完。{@code body} 是請求本文原樣的 JSON 物件（鍵缺席與 {@code null} 是兩件事）；
     * 違規丟 {@link UnprocessableException}，通過回命令（{@code note} 缺鍵時為空字串）。
     */
    public static Command set(String id, Map<String, Object> body) {
        Check check = new Check();
        id(check, id);
        Integer rank = rank(check, body.get("rank"));
        String note = "";
        if (body.containsKey("note")) {
            note = note(check, body.get("note"));
        }
        check.throwIfAny();
        return new Command(id, rank, note);
    }

    private static void id(Check check, String id) {
        if (id == null || !ISSUE_ID.matcher(id).matches()) {
            check.add("id", "id 須為 OBS-SI-<三位以上數字>、PROP-SI-<三位以上數字> 或 DEF-<數字>-<數字>");
        }
    }

    private static Integer rank(Check check, Object raw) {
        if (raw == null) {
            check.add("rank", "rank 為必填（缺鍵或 null 不是清除；要清除請用 DELETE）");
            return null;
        }
        BigInteger value = integerOf(raw);
        if (value == null) {
            check.add("rank", "rank 須為整數（不收字串、小數、布林、陣列與物件）");
            return null;
        }
        if (value.compareTo(BIG_MIN) < 0 || value.compareTo(BIG_MAX) > 0) {
            check.add("rank", "rank 須介於 " + RANK_MIN + " 與 " + RANK_MAX);
            return null;
        }
        return value.intValueExact();
    }

    /** JSON 整數（Jackson 對映成 Integer／Long／BigInteger）；小數、字串、布林、容器一律不是。 */
    private static BigInteger integerOf(Object raw) {
        if (raw instanceof Integer || raw instanceof Long || raw instanceof Short || raw instanceof Byte) {
            return BigInteger.valueOf(((Number) raw).longValue());
        }
        return raw instanceof BigInteger big ? big : null;
    }

    private static String note(Check check, Object raw) {
        if (!(raw instanceof String text)) {
            check.add("note", "note 須為字串（缺鍵才是空字串；null 與數字都不收）");
            return null;
        }
        if (hasForbiddenChar(text)) {
            check.add("note", "note 不可含控制字元（換行、TAB 等）或無效字元");
            return null;
        }
        int length = text.codePointCount(0, text.length());
        if (length > NOTE_MAX) {
            check.add("note", "note 為 " + length + " 個字元，超過上限 " + NOTE_MAX);
            return null;
        }
        return text;
    }

    /** U+0000～U+001F、U+007F，或孤立的代理字元（高代理後須緊接低代理）。 */
    private static boolean hasForbiddenChar(String value) {
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (c < 0x20 || c == 0x7F) {
                return true;
            }
            if (Character.isHighSurrogate(c)) {
                if (i + 1 >= value.length() || !Character.isLowSurrogate(value.charAt(i + 1))) {
                    return true;
                }
                i++;
            } else if (Character.isLowSurrogate(c)) {
                return true;
            }
        }
        return false;
    }

    /** 收集違規、一次丟出。 */
    private static final class Check {

        private final List<Violation> violations = new ArrayList<>();

        void add(String field, String message) {
            violations.add(new Violation(field, message));
        }

        void throwIfAny() {
            if (violations.isEmpty()) {
                return;
            }
            List<Map<String, Object>> asMaps = new ArrayList<>();
            for (Violation violation : violations) {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("field", violation.field());
                item.put("message", violation.message());
                asMaps.add(item);
            }
            throw new UnprocessableException("請求欄位未通過檢查（" + violations.size() + " 項）", INVALID_REQUEST, List.of(),
                    violations, Map.of("violations", asMaps));
        }
    }
}
