package com.aisdlc.console.domain.model.imports;

/**
 * 單一有界閘違規（契約 §3.3.5；{@code import_records.last_parse_errors} 的元素）。
 *
 * @param gate     閘名稱（逐字常數：{@code max_steps}、{@code cycle}…）
 * @param detail   給人看的完整原因（不截斷）
 * @param location 違規位置，例如 {@code goals[0].tasks[3].description}；沒有位置的閘（brain_*）為 null
 */
public record GateError(String gate, String detail, String location) {

    /** 閘名稱（逐字常數；前端 {@code GateName} 與此相同）。 */
    public static final String MAX_STEPS = "max_steps";
    public static final String CYCLE = "cycle";
    public static final String EMPTY_PROMPT = "empty_prompt";
    public static final String PROMPT_TOO_LONG = "prompt_too_long";
    public static final String BRAIN_UNSUPPORTED = "brain_unsupported";
    public static final String BRAIN_FAILED = "brain_failed";
}
