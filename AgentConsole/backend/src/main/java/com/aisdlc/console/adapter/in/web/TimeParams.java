package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.domain.exception.ValidationException;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.format.DateTimeParseException;
import java.util.regex.Pattern;

/**
 * 查詢參數裡的時間（{@code from}／{@code to}）：ISO-8601 帶 offset。
 *
 * <p>未編碼的 {@code +}（例：{@code 2026-10-15T16:40:00+08:00}）在查詢字串會被解碼成空白——呼叫端照理要編成 {@code %2B}，
 * 但這是最常見的疏忽，所以把「結尾的 {@code 空白HH:mm}」還原成 {@code +HH:mm}，而不是回一個令人困惑的 400。
 */
final class TimeParams {

    private static final Pattern LOST_PLUS = Pattern.compile(" (\\d{2}:\\d{2})$");

    private TimeParams() {
    }

    /** null／空白回 null（取預設）；格式不合 → 400（欄位名即參數名）。 */
    static Instant parse(String name, String raw) {
        if (raw == null || raw.isBlank()) {
            return null;
        }
        String text = LOST_PLUS.matcher(raw.strip()).replaceFirst("+$1");
        try {
            return OffsetDateTime.parse(text).toInstant();
        } catch (DateTimeParseException e) {
            throw ValidationException.of(name, name + " 必須是帶 offset 的 ISO-8601 時間（例：2026-10-15T08:40:00Z）");
        }
    }
}
