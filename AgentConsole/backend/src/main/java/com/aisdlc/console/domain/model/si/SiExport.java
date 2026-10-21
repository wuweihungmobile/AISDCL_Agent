package com.aisdlc.console.domain.model.si;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Bridge {@code GET /si/*} 回的 export 物件（SelfImproving 唯讀鏡像；TCS-SelfImprovingMirror-P1b R9、R10）。
 *
 * <p>{@code raw} 是 Bridge 的原樣 JSON：<b>snake_case 鍵、值未動</b>（含 {@code null}、字串、巢狀物件與陣列），鍵序保留。
 * backend 不重算——不折疊事件、不算 digest、不判 NE、不補 {@code generated_at}；欄名轉換只發生在回應邊界
 * （{@code SiKeyNames}），這裡持有的永遠是來源的樣子，所以「缺鍵」與「值為 null」在此仍是兩件事。
 *
 * @param raw Bridge 本文解析後的最外層物件（不可變檢視；允許 null 值，所以不用 {@code Map.copyOf}）
 */
public record SiExport(Map<String, Object> raw) {

    public SiExport {
        raw = raw == null ? Map.of() : Collections.unmodifiableMap(new LinkedHashMap<>(raw));
    }
}
