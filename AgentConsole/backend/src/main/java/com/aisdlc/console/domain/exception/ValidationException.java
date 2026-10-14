package com.aisdlc.console.domain.exception;

import java.util.List;
import java.util.Map;

/** 輸入違反領域規則（對映 HTTP 400）。 */
public final class ValidationException extends DomainException {

    private final List<Violation> violations;

    public ValidationException(String message, String reason, List<Violation> violations,
                               Map<String, Object> details) {
        super(message, reason, details);
        this.violations = violations == null ? List.of() : List.copyOf(violations);
    }

    /** 只有單一欄位違規的便捷建構。 */
    public static ValidationException of(String field, String message) {
        return new ValidationException(message, null, List.of(new Violation(field, message)), Map.of());
    }

    /** 帶 reason 與結構化 details 的單欄位違規（例：依賴成環）。 */
    public static ValidationException of(String field, String message, String reason,
                                         Map<String, Object> details) {
        return new ValidationException(message, reason, List.of(new Violation(field, message)), details);
    }

    public List<Violation> violations() {
        return violations;
    }
}
