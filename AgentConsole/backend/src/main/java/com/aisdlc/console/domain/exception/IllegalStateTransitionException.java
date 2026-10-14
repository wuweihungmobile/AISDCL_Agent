package com.aisdlc.console.domain.exception;

import java.util.Map;

/** 違反附錄 B 狀態機的轉移（對映 HTTP 409）。 */
public final class IllegalStateTransitionException extends ConflictException {

    public IllegalStateTransitionException(String entity, String from, String to) {
        super(entity + "狀態不可由 " + from + " 轉移為 " + to,
                "非法狀態轉移",
                Map.of("entity", entity, "from", from, "to", to));
    }
}
