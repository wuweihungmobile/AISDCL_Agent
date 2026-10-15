package com.aisdlc.console.application.service;

import org.slf4j.MDC;

import java.util.function.Supplier;

/**
 * traceId 的 MDC 約定（契約 §0.4 第 6 點，C-12；NFR-9.4-04）。{@code TraceIdFilter} 為每個使用者請求把 traceId 放進
 * MDC（鍵 {@value #MDC_KEY}），出站的 Bridge 介面卡從同一個 MDC 取值、放進 {@code X-Trace-Id} 標頭。沒有請求上下文的背景執行緒
 * （事件消費者、啟動對帳）要自己在 MDC 裡放該 run 的 traceId——{@link #within} 做這件事並在結束後還原。
 */
final class TraceIds {

    static final String MDC_KEY = "traceId";

    private TraceIds() {
    }

    /** 目前執行緒的 traceId；沒有請求上下文（背景執行緒）為 null。 */
    static String current() {
        return MDC.get(MDC_KEY);
    }

    /** 在指定的 traceId 脈絡下執行；結束（含例外）後還原原本的值。 */
    static <T> T within(String traceId, Supplier<T> action) {
        String previous = MDC.get(MDC_KEY);
        MDC.put(MDC_KEY, traceId);
        try {
            return action.get();
        } finally {
            if (previous == null) {
                MDC.remove(MDC_KEY);
            } else {
                MDC.put(MDC_KEY, previous);
            }
        }
    }

    static void within(String traceId, Runnable action) {
        within(traceId, () -> {
            action.run();
            return null;
        });
    }
}
