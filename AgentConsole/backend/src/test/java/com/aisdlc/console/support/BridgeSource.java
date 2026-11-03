package com.aisdlc.console.support;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 真 Bridge 原始碼的<b>唯讀</b>取數器（ResearchToPRD P0 修復棒；INT-01／03／08 的共同根因＝console-api 的 DTO 與迷你 Bridge 各自照「自己猜的」Bridge 回應形狀寫，
 * 兩端互相印證而都錯）。測試直接從 {@code engine-bridge/app/**} 的 Python 原始碼取出 Bridge 宣告的鍵集合，讓迷你 Bridge 與 DTO 的形狀有「源頭」可對：Bridge 改了形狀而
 * 這邊沒跟上，單元測試當場紅，而不是等到 Docker 全棧才現形。只讀文字、不執行 Python；只認本專案 Bridge 的三種宣告寫法（見各方法），認不得就 fail-loud。
 */
public final class BridgeSource {

    private BridgeSource() {
    }

    /** {@code engine-bridge/app/<segments>} 的全文（UTF-8）；工作目錄是 backend 專案根，所以往上一層。 */
    public static String source(String... appSegments) {
        String[] all = new String[appSegments.length + 2];
        all[0] = "engine-bridge";
        all[1] = "app";
        System.arraycopy(appSegments, 0, all, 2, appSegments.length);
        Path path = Path.of("..", all);
        try {
            return Files.readString(path, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("讀不到 Bridge 原始碼 " + path.toAbsolutePath(), e);
        }
    }

    /**
     * 模組層字串常數集合，依宣告順序：{@code NAME: tuple[str, ...] = ("a", "b")} 或 {@code NAME: frozenset[str] = frozenset({"a", "b"})}
     * （後者回傳的順序是宣告順序，不是集合順序）。找不到宣告或內容為空＝丟例外。
     */
    public static List<String> constants(String name, String... appSegments) {
        Matcher declaration = Pattern.compile("(?m)^" + Pattern.quote(name) + "\\s*:[^=\\n]*=\\s*(?:frozenset\\()?[({]([^)}]*)[)}]").matcher(source(appSegments));
        if (!declaration.find()) {
            throw new IllegalStateException("Bridge 原始碼找不到字串常數集合 " + name + "（" + String.join("/", appSegments) + "）");
        }
        List<String> out = quoted(declaration.group(1));
        if (out.isEmpty()) {
            throw new IllegalStateException(name + " 的宣告沒有任何字串");
        }
        return out;
    }

    /**
     * 函式 {@code def <function>(…)} 第一個 {@code return {…}} 的字典字面值的鍵（依出現順序）。只支援<b>扁平</b>的字面值（值內不得再有 {@code {}}）——
     * 值是巢狀字典時丟例外，免得悄悄少讀鍵。
     */
    public static List<String> returnedKeys(String function, String... appSegments) {
        String text = source(appSegments);
        int def = text.indexOf("def " + function + "(");
        if (def < 0) {
            throw new IllegalStateException("Bridge 原始碼找不到函式 " + function + "（" + String.join("/", appSegments) + "）");
        }
        int open = text.indexOf("return {", def);
        if (open < 0) {
            throw new IllegalStateException(function + " 沒有 return {…} 字典字面值");
        }
        int start = open + "return {".length();
        int end = text.indexOf('}', start);
        String body = text.substring(start, end);
        if (body.indexOf('{') >= 0) {
            throw new IllegalStateException(function + " 的回傳字面值有巢狀字典，BridgeSource 只支援扁平字面值");
        }
        List<String> keys = new ArrayList<>();
        Matcher key = Pattern.compile("\"([A-Za-z0-9_]+)\"\\s*:").matcher(body);
        while (key.find()) {
            keys.add(key.group(1));
        }
        if (keys.isEmpty()) {
            throw new IllegalStateException(function + " 的回傳字面值沒有任何鍵");
        }
        return keys;
    }

    private static List<String> quoted(String text) {
        List<String> out = new ArrayList<>();
        Matcher item = Pattern.compile("\"([A-Za-z0-9_]+)\"").matcher(text);
        while (item.find()) {
            out.add(item.group(1));
        }
        return out;
    }
}
