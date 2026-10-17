package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.exception.Violations;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.regex.Pattern;

/**
 * 核准凍結請求的值規則（契約 §1.10.2「Request」與驗證順序第 2 項；純 Java）。Backend 在<b>專案存在之後</b>才驗（404 先於 400，與 execute 同），
 * 所以這裡不是 Bean Validation：違規一律累積成 {@code ValidationException}（400，{@code errors[].field} 是欄位名）。
 *
 * <p>只做 Console 能判斷的事：格式、長度、與專案已綁定規格檔的一致性。檔案存在與否、是否含 TCS、摘要是否吻合，都是 Bridge 的事
 * （它有檔案系統；Console 在 Docker 內看不到使用者專案）。
 */
public final class SddFreezeRules {

    public static final int MAX_REASON = 500;
    public static final int MAX_DOCS = 20;
    public static final int MAX_DOC_PATH = 500;

    private static final Pattern STAGE = Pattern.compile("^[A-Za-z0-9._-]{1,64}$");
    private static final Pattern DIGEST = Pattern.compile("^sha256:[0-9a-f]{64}$");
    private static final Pattern CONTROL_CHARS = Pattern.compile("\\p{Cntrl}");
    private static final Pattern DRIVE_LETTER = Pattern.compile("^[A-Za-z]:");

    private SddFreezeRules() {
    }

    /** 通過驗證、可送給 Bridge 的值（{@code docs} 與 {@code expectedDigests} 的鍵已正規化為相對 root 的 POSIX 路徑）。 */
    public record Checked(String reason, String stage, List<String> docs, Map<String, String> expectedDigests) {
    }

    /**
     * @param docs            null＝省略（取專案已綁定的規格檔）；空清單是違規（1～20 項）
     * @param executionPath   專案根（絕對路徑，Console 驗過格式）
     * @param sddSpecFile     專案已綁定的規格檔（絕對路徑）；null＝尚未綁定
     */
    public static Checked check(Violations v, String reason, String stage, List<String> docs,
                                Map<String, String> expectedDigests, String executionPath, String sddSpecFile) {
        String checkedReason = checkReason(v, reason);
        String checkedStage = checkStage(v, stage);
        List<String> checkedDocs = checkDocs(v, docs, executionPath, sddSpecFile);
        Map<String, String> checkedDigests = checkDigests(v, expectedDigests, checkedDocs);
        return new Checked(checkedReason, checkedStage, checkedDocs, checkedDigests);
    }

    private static String checkReason(Violations v, String reason) {
        if (reason == null || reason.isBlank()) {
            v.add("reason", "核准理由不可為空");
            return null;
        }
        String text = reason.strip();
        if (text.length() > MAX_REASON) {
            v.add("reason", "核准理由長度不可超過 " + MAX_REASON + " 字元（不會靜默截斷）");
            return null;
        }
        if (CONTROL_CHARS.matcher(text).find()) {
            v.add("reason", "核准理由不可包含控制字元（含換行）");
            return null;
        }
        return text;
    }

    private static String checkStage(Violations v, String stage) {
        if (stage == null) {
            return null;
        }
        if (!STAGE.matcher(stage).matches()) {
            v.add("stage", "stage 須符合 ^[A-Za-z0-9._-]{1,64}$");
            return null;
        }
        return stage;
    }

    private static List<String> checkDocs(Violations v, List<String> docs, String executionPath, String sddSpecFile) {
        if (docs == null) {
            return defaultDocs(v, executionPath, sddSpecFile);
        }
        if (docs.isEmpty() || docs.size() > MAX_DOCS) {
            v.add("docs", "docs 須為 1～" + MAX_DOCS + " 項");
            return null;
        }
        List<String> normalized = new ArrayList<>();
        for (int i = 0; i < docs.size(); i++) {
            String doc = normalizeDoc(v, "docs[" + i + "]", docs.get(i));
            if (doc == null) {
                return null;
            }
            normalized.add(doc);
        }
        if (sddSpecFile != null && !containsSpecFile(normalized, executionPath, sddSpecFile)) {
            v.add("docs", "docs 須包含專案已綁定的規格檔（" + sddSpecFile + "）");
            return null;
        }
        return List.copyOf(normalized);
    }

    /** 省略 docs：專案已有規格檔且在專案根之下時，取它相對專案根的路徑；其餘都是違規（沒有東西可凍結）。 */
    private static List<String> defaultDocs(Violations v, String executionPath, String sddSpecFile) {
        if (sddSpecFile == null) {
            v.add("docs", "專案尚未綁定規格檔，請明示 docs（相對專案根的 POSIX 路徑）");
            return null;
        }
        Optional<String> relative = SpecPaths.relativeTo(executionPath, sddSpecFile);
        if (relative.isEmpty()) {
            v.add("docs", "專案已綁定的規格檔不在專案根（executionPath）之下，無法換算成相對路徑，請明示 docs");
            return null;
        }
        String doc = normalizeDoc(v, "docs", relative.get());      // 同樣的正規化（重複分隔符、.、..）
        return doc == null ? null : List.of(doc);
    }

    private static boolean containsSpecFile(List<String> docs, String executionPath, String sddSpecFile) {
        String base = executionPath.strip().replace('\\', '/');
        String prefix = base.endsWith("/") ? base : base + "/";
        return docs.stream().anyMatch(doc -> SpecPaths.same(prefix + doc, sddSpecFile));
    }

    private static Map<String, String> checkDigests(Violations v, Map<String, String> digests, List<String> docs) {
        if (digests == null || digests.isEmpty()) {
            return null;
        }
        Map<String, String> normalized = new LinkedHashMap<>();
        for (Map.Entry<String, String> entry : digests.entrySet()) {
            String key = normalizeDoc(v, "expectedDigests", entry.getKey());
            if (key == null) {
                return null;
            }
            if (docs != null && !docs.contains(key)) {
                v.add("expectedDigests", "expectedDigests 的鍵必須都在 docs 內：" + key);
                return null;
            }
            if (entry.getValue() == null || !DIGEST.matcher(entry.getValue()).matches()) {
                v.add("expectedDigests", "摘要須為 sha256:<64 位小寫 hex>：" + key);
                return null;
            }
            normalized.put(key, entry.getValue());
        }
        return Map.copyOf(normalized);
    }

    /**
     * 一個 doc 路徑正規化為相對 root 的 POSIX 路徑：反斜線視為分隔符、去掉 {@code .} 與空段；絕對路徑（{@code /}、磁碟機代號、UNC）、
     * {@code ..}、控制字元、空白與超長一律違規（回 null 並記入 {@code v}）。
     */
    static String normalizeDoc(Violations v, String field, String raw) {
        if (raw == null || raw.isBlank()) {
            v.add(field, "路徑不可為空白");
            return null;
        }
        if (CONTROL_CHARS.matcher(raw).find()) {
            v.add(field, "路徑不可包含控制字元");
            return null;
        }
        String text = raw.replace('\\', '/');
        if (text.startsWith("/") || DRIVE_LETTER.matcher(text).find()) {
            v.add(field, "路徑須是相對專案根的相對路徑，不可為絕對路徑：" + raw);
            return null;
        }
        List<String> segments = new ArrayList<>();
        for (String segment : text.split("/")) {
            if (segment.isEmpty() || ".".equals(segment)) {
                continue;
            }
            if ("..".equals(segment)) {
                v.add(field, "路徑不可包含 ..：" + raw);
                return null;
            }
            segments.add(segment);
        }
        String joined = String.join("/", segments);
        if (joined.isEmpty() || joined.length() > MAX_DOC_PATH) {
            v.add(field, "路徑須為 1～" + MAX_DOC_PATH + " 字元：" + raw);
            return null;
        }
        return joined;
    }
}
