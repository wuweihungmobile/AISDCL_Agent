package com.aisdlc.console.domain.model.backup;

import java.util.regex.Pattern;

/**
 * 輸出尾段的機密遮罩（TCS-SysAdminBackup-20261027 R-BK-42、D-BK-T15；純函式，無 Spring）。遮罩有兩道、規格相同：sidecar 的 {@code job-run.sh}
 * （perl）與 console-api 的本類別各遮罩一次——console-api <b>不信任</b> sidecar 已遮罩，所以 API 回應、資料庫的 {@code detail} 與審計都經過這裡。
 * 兩邊對探針檔 {@code docker/pgbackrest/tests/fixtures/mask-probes.txt} 的每一行必須產出逐字相同的輸出（探針單一來源，{@code BackupDomainTest} 與
 * {@code BackupSidecarContractIT} 共讀）。
 *
 * <p>形狀（不分大小寫；只認形狀，<b>不因 {@code example}／{@code fake} 之類的佔位詞放行</b>）：
 * <ol>
 *   <li>鍵名含 {@code pass}／{@code secret}／{@code key}／{@code token} 且後接 {@code =} 或 {@code :}（中間容許一個收尾引號與空白）⇒ 值
 *       （整個引號字串，或到空白、逗號、分號、{@code &}、引號為止）改 {@code ***}，保留鍵名與分隔；</li>
 *   <li>AWS 存取金鑰 id（{@code AKIA} 加 16 個大寫英數）⇒ {@code ***}；</li>
 *   <li>連線字串 {@code scheme://user:密碼@host} ⇒ 密碼改 {@code ***}。</li>
 * </ol>
 * 冪等（遮罩後再遮罩不變）。<b>逐行處理</b>（與 perl 的 {@code -p} 同口徑：形狀不跨行）。
 * 取尾段的順序是「先遮罩、後取最後 N 個 code point」（{@link #maskedTail}）：先截斷再遮罩會讓被截斷的半個機密漏出。
 */
public final class BackupMasker {

    /** 輸出尾段的字元上限（code point）。 */
    public static final int TAIL_MAX = 2000;

    private static final String MASK = "***";

    // 三條規則與 job-run.sh 的 mask_output（perl）逐式對應；改一邊必須改另一邊，探針檔是兩邊共同的判準。
    private static final Pattern AWS_KEY_ID = Pattern.compile("(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}(?![A-Za-z0-9])");
    private static final Pattern CONNECTION_STRING =
            Pattern.compile("([A-Za-z][A-Za-z0-9+.\\-]*://[^\\s:/@]+:)[^\\s@/]+(@)");
    private static final Pattern KEYED_VALUE = Pattern.compile(
            "((?:pass|secret|key|token)[A-Za-z0-9_.\\-]{0,64}[\"']?\\s*[=:]\\s*)(\"[^\"]*\"|'[^']*'|[^\\s,;&\"']+)",
            Pattern.CASE_INSENSITIVE);

    private BackupMasker() {
    }

    /** 遮罩整段文字（逐行）；{@code null} 當空字串。 */
    public static String mask(String text) {
        if (text == null || text.isEmpty()) {
            return "";
        }
        String[] lines = text.split("\n", -1);
        StringBuilder out = new StringBuilder(text.length());
        for (int i = 0; i < lines.length; i++) {
            if (i > 0) {
                out.append('\n');
            }
            out.append(maskLine(lines[i]));
        }
        return out.toString();
    }

    private static String maskLine(String line) {
        String masked = AWS_KEY_ID.matcher(line).replaceAll(MASK);
        masked = CONNECTION_STRING.matcher(masked).replaceAll("$1" + MASK + "$2");
        return KEYED_VALUE.matcher(masked).replaceAll("$1" + MASK);
    }

    /** 最後 {@code maxCodePoints} 個 code point（以 code point 計，不以 UTF-16 單元計，不會截出孤立的代理字元）；{@code null} 當空字串。 */
    public static String tail(String text, int maxCodePoints) {
        if (text == null || text.isEmpty() || maxCodePoints <= 0) {
            return "";
        }
        int count = text.codePointCount(0, text.length());
        if (count <= maxCodePoints) {
            return text;
        }
        return text.substring(text.offsetByCodePoints(0, count - maxCodePoints));
    }

    /** 先遮罩、後取最後 {@code maxCodePoints} 個 code point（R-BK-42 的順序）。 */
    public static String maskedTail(String text, int maxCodePoints) {
        return tail(mask(text), maxCodePoints);
    }
}
