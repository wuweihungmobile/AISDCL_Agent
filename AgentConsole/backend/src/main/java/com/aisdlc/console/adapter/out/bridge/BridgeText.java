package com.aisdlc.console.adapter.out.bridge;

import java.util.regex.Pattern;

/**
 * Bridge 自由文字欄位（狀態事件與快照的 {@code reason}、告警事件的 {@code message}）進入 Console 時的清潔：去掉行程編號（pid）。
 *
 * <p>為什麼要有它：契約 §1.2.3 要求回應「不外露 pid」，§3.1.2 與 E2E-14 第 8 列再要求「回應與日誌沒有 pid」；但 Bridge 自己的
 * 狀態文字就帶 pid——每個 run 一開始的狀態是 {@code 引擎已啟動（pid=<行程編號>，第 <n> 次 spawn）}，強制終止時的告警是
 * {@code …已強制終止 pid=[<編號>, …]}——而 Console 把它們逐字轉成批次詳情的 {@code reason} 與 SSE 的 {@code status-change}／{@code alert}。
 * 在出口（介面卡）統一去掉，下游的投影、重播與回應就都乾淨了；Bridge 自己的日誌與審計不受影響。
 *
 * <p>只認「pid＝數字」與「pid＝[數字清單]」這兩種 Bridge 實際會寫的形狀，連同它後面的一個逗號一起去掉（
 * {@code （pid=123，第 1 次 spawn）} → {@code （第 1 次 spawn）}）；文字裡沒有 pid 就原樣回傳。
 */
final class BridgeText {

    /** {@code pid=123}、{@code pid=[123, 456]}（含全形等號冒號），及其後緊接的一個逗號與空白；{@code \b} 避免誤傷 {@code rapid=3} 這類字。 */
    private static final Pattern PID = Pattern.compile(
            "\\bpid\\s*[=:：]\\s*(?:\\[[^\\]]*\\]|\\d+)\\s*[，,]?\\s*", Pattern.CASE_INSENSITIVE);

    private BridgeText() {
    }

    /** 去掉文字中的 pid；null 與沒有 pid 的文字原樣回傳。去除後結尾多出的空白一併修掉。 */
    static String withoutPid(String text) {
        if (text == null || !PID.matcher(text).find()) {
            return text;
        }
        return PID.matcher(text).replaceAll("").stripTrailing();
    }
}
