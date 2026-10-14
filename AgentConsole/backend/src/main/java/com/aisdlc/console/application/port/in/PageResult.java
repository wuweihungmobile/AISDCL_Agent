package com.aisdlc.console.application.port.in;

import java.util.List;
import java.util.function.Function;

/**
 * 分頁結果（page 從 0 起算）；對應 PRD §7.2 的分頁封包欄位。
 *
 * @param content       本頁內容
 * @param page          頁碼（0-based）
 * @param size          每頁筆數
 * @param totalElements 符合條件的總筆數
 */
public record PageResult<T>(List<T> content, int page, int size, long totalElements) {

    public int totalPages() {
        return size <= 0 ? 0 : (int) ((totalElements + size - 1) / size);
    }

    public <R> PageResult<R> map(Function<? super T, ? extends R> mapper) {
        return new PageResult<>(content.stream().<R>map(mapper).toList(), page, size, totalElements);
    }
}
