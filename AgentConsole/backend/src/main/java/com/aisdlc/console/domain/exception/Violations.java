package com.aisdlc.console.domain.exception;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** 收集多個欄位違規後一次丟出（比「遇到第一個就停」更適合表單回饋）。 */
public final class Violations {

    private final List<Violation> items = new ArrayList<>();

    public Violations add(String field, String message) {
        items.add(new Violation(field, message));
        return this;
    }

    public boolean isEmpty() {
        return items.isEmpty();
    }

    /** 有任何違規即丟 {@link ValidationException}（HTTP 400）。 */
    public void throwIfAny() {
        if (!items.isEmpty()) {
            throw new ValidationException("Validation failed", null, items, Map.of());
        }
    }
}
