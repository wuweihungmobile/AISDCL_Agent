package com.aisdlc.console.adapter.in.web;

import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Schema;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 設定分類的路徑參數（契約 §1.5：六個分類）。只影響 OpenAPI 文件——列舉讓前端產生的型別是字面量聯集；
 * 執行期不驗列舉：分類不在六個之內一律是 404（{@code 設定分類不存在}），不是 400（契約 §1.5.2）。
 * 值域與 {@code ConfigCatalog.CATEGORIES} 的一致性由 OpenApiIT 釘住。
 */
@Target(ElementType.PARAMETER)
@Retention(RetentionPolicy.RUNTIME)
@Parameter(description = "設定分類",
        schema = @Schema(allowableValues = {"model", "agent", "execution", "monitor", "autoclaude", "sdd"}))
@interface CategoryParam {
}
