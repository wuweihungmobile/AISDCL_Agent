package com.aisdlc.console.adapter.in.web.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;

/** 編輯解析結果（契約 §1.1.4）：整棵樹覆寫；陣列順序即排序；成功後撤銷既有 signoff。 */
public record EditParsedResultRequest(
        @NotNull(message = "parsedResult 不可為空") @Valid ParsedResultDto parsedResult) {
}
