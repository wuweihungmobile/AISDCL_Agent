package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.PageResult;
import jakarta.validation.constraints.NotNull;

import java.util.List;
import java.util.function.Function;

/** 分頁資料（PRD §7.2 分頁格式）：放在 {@link ApiResult#data()} 內。 */
public record PageData<T>(
        @NotNull List<T> content,
        @NotNull int page,
        @NotNull int size,
        @NotNull long totalElements,
        @NotNull int totalPages) {

    public static <S, T> PageData<T> of(PageResult<S> result, Function<? super S, ? extends T> mapper) {
        PageResult<T> mapped = result.map(mapper);
        return new PageData<>(mapped.content(), mapped.page(), mapped.size(), mapped.totalElements(),
                mapped.totalPages());
    }
}
