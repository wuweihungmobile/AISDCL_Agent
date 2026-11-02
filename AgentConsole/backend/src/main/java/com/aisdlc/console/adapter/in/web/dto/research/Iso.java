package com.aisdlc.console.adapter.in.web.dto.research;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeFormatterBuilder;
import java.util.List;
import java.util.Map;

/**
 * 研究 DTO 共用的小工具：時間一律輸出 ISO-8601 <b>帶 offset</b>、UTC 以 {@code +00:00} 表示（契約 §0.1：不得 naive；不用 {@code Z}，與引擎回應同一寫法），
 * 以及從 Bridge 本文（{@code Map<String, Object>}）取值的寬鬆讀法（缺鍵、型別不符一律給預設值，不丟例外——本文是第三方產出的資料）。
 */
final class Iso {

    private static final DateTimeFormatter FORMAT = new DateTimeFormatterBuilder()
            .append(DateTimeFormatter.ISO_LOCAL_DATE_TIME).appendOffset("+HH:MM", "+00:00").toFormatter();

    private Iso() {
    }

    /** UTC、{@code +00:00}；null→null。 */
    static String of(OffsetDateTime time) {
        return time == null ? null : FORMAT.format(time.withOffsetSameInstant(ZoneOffset.UTC));
    }

    /** 日期 {@code YYYY-MM-DD}；null→null。 */
    static String of(LocalDate date) {
        return date == null ? null : date.toString();
    }

    static String text(Object value) {
        return value == null ? null : value.toString();
    }

    static String text(Object value, String fallback) {
        return value == null ? fallback : value.toString();
    }

    static boolean flag(Object value) {
        return Boolean.TRUE.equals(value);
    }

    static Integer integer(Object value) {
        return value instanceof Number n ? Integer.valueOf(n.intValue()) : null;
    }

    static Long longValue(Object value) {
        return value instanceof Number n ? Long.valueOf(n.longValue()) : null;
    }

    @SuppressWarnings("unchecked")
    static Map<String, Object> map(Object value) {
        return value instanceof Map<?, ?> m ? (Map<String, Object>) m : Map.of();
    }

    static List<?> list(Object value) {
        return value instanceof List<?> l ? l : List.of();
    }

    static List<String> strings(Object value) {
        return list(value).stream().filter(item -> item != null).map(Object::toString).toList();
    }
}
