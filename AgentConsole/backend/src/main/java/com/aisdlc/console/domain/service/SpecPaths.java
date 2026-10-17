package com.aisdlc.console.domain.service;

import java.util.Optional;
import java.util.regex.Pattern;

/**
 * 專案根與規格路徑的純字串運算（契約 §1.10.2、§1.10.8；純 Java，不碰檔案系統，與平台無關）。
 *
 * <p>為什麼不用 {@code java.nio.file.Path}：Console 跑在 Linux 容器、路徑卻可能是 Windows 主機上的 {@code D:\work\proj} 或 UNC
 * （{@link FieldRules#executionPath} 三種格式都收），{@code Path.of} 在不同平台對它們的解讀不同。這裡只做三件事：
 * 兩種分隔符一視同仁、Windows 風格的路徑不分大小寫、算相對路徑與父目錄。
 */
public final class SpecPaths {

    /** 磁碟機代號（{@code C:}）或 UNC（{@code \\server\share}／{@code //server/share}）開頭＝Windows 風格，比對不分大小寫。 */
    private static final Pattern WINDOWS_LIKE = Pattern.compile("^(?:[A-Za-z]:|\\\\\\\\|//)");
    private static final Pattern DRIVE_ROOT = Pattern.compile("^[A-Za-z]:/$");

    private SpecPaths() {
    }

    /** 兩個路徑是否指向同一處（分隔符不分、尾端分隔符不計；任一個是 Windows 風格則不分大小寫）。 */
    public static boolean same(String a, String b) {
        if (a == null || b == null) {
            return false;
        }
        String left = slashed(a);
        String right = slashed(b);
        return ignoreCase(a, b) ? left.equalsIgnoreCase(right) : left.equals(right);
    }

    /** {@code child} 是否等於 {@code base}，或在 {@code base} 之下。 */
    public static boolean isUnder(String child, String base) {
        return same(child, base) || relativeTo(base, child).isPresent();
    }

    /**
     * {@code child} 相對 {@code base} 的 POSIX 路徑（保持 {@code child} 原本的大小寫）；{@code child} 不在 {@code base} 之下、
     * 或兩者相同時為 empty。
     */
    public static Optional<String> relativeTo(String base, String child) {
        if (base == null || child == null) {
            return Optional.empty();
        }
        String b = slashed(base);
        String c = slashed(child);
        String prefix = b.endsWith("/") ? b : b + "/";
        if (c.length() > prefix.length() && c.regionMatches(ignoreCase(base, child), 0, prefix, 0, prefix.length())) {
            String rest = c.substring(prefix.length());
            while (rest.startsWith("/")) {
                rest = rest.substring(1);              // 重複的分隔符（{@code /work/proj//docs}）不是絕對路徑
            }
            return rest.isEmpty() ? Optional.empty() : Optional.of(rest);
        }
        return Optional.empty();
    }

    /**
     * 檔案路徑的父目錄（保持原本的分隔符風格）：{@code /spec/cart.md}→{@code /spec}、{@code D:\a\b.md}→{@code D:\a}、
     * {@code /x.md}→{@code /}、{@code D:\x.md}→{@code D:\}；沒有分隔符回空字串。
     */
    public static String parentOf(String path) {
        String text = path.strip();
        int cut = Math.max(text.lastIndexOf('/'), text.lastIndexOf('\\'));
        if (cut < 0) {
            return "";
        }
        if (cut == 0) {
            return text.substring(0, 1);
        }
        if (cut == 2 && text.charAt(1) == ':') {
            return text.substring(0, 3);
        }
        return text.substring(0, cut);
    }

    private static boolean ignoreCase(String a, String b) {
        return WINDOWS_LIKE.matcher(a.strip()).find() || WINDOWS_LIKE.matcher(b.strip()).find();
    }

    /** 反斜線換成斜線、去前後空白與尾端分隔符（根目錄 {@code /} 與 {@code C:/} 保留）。 */
    private static String slashed(String path) {
        String text = path.strip().replace('\\', '/');
        while (text.length() > 1 && text.endsWith("/") && !DRIVE_ROOT.matcher(text).matches()) {
            text = text.substring(0, text.length() - 1);
        }
        return text;
    }
}
