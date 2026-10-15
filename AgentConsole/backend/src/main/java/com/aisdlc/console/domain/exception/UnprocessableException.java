package com.aisdlc.console.domain.exception;

import com.aisdlc.console.domain.model.imports.GateError;

import java.util.List;
import java.util.Map;

/**
 * 有界閘、消毒或政策拒絕（對映 HTTP 422）：Bridge 的 422 原因逐字帶出、SSRF／allowlist 檢查未通過、
 * 解析結果未通過有界閘（{@code gateErrors} 一次列出全部違規，不截斷）。
 */
public final class UnprocessableException extends DomainException {

    private final List<GateError> gateErrors;
    private final List<Violation> violations;

    public UnprocessableException(String message, String reason, Map<String, Object> details) {
        this(message, reason, List.of(), List.of(), details);
    }

    public UnprocessableException(String message, String reason, List<GateError> gateErrors,
                                  List<Violation> violations, Map<String, Object> details) {
        super(message, reason, details);
        this.gateErrors = gateErrors == null ? List.of() : List.copyOf(gateErrors);
        this.violations = violations == null ? List.of() : List.copyOf(violations);
    }

    /** 有界閘違規（解析結果未通過有界閘時非空）。 */
    public List<GateError> gateErrors() {
        return gateErrors;
    }

    /** 一般欄位違規（例：{@code SDD 規格檢查未通過} 的 {@code specDir}）。 */
    public List<Violation> violations() {
        return violations;
    }
}
