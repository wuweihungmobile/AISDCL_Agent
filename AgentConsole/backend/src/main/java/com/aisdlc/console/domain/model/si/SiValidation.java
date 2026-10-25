package com.aisdlc.console.domain.model.si;

import java.util.List;

/**
 * 觀察列預檢結果（Bridge {@code POST /si/observations:validate}＝根層 {@code obs-add --dry-run} 的輸出；TCS-SelfImprovingDecide-P2b W4、W11）。
 * backend 不重算：值逐項取自 Bridge 的物件（{@code row_bytes}→{@link #rowBytes}、{@code row_max_bytes}→{@link #rowMaxBytes}）。
 *
 * @param ok          預檢是否通過（{@code false} 仍是 200：findings 說明哪裡不合）
 * @param row         預覽列全文（通過才有；否則空字串）
 * @param rowBytes    預覽列的 UTF-8 位元組數
 * @param rowMaxBytes 根層協定參數的列位元組上限；根層量不到時為 {@code null}
 * @param findings    不合的原因（{@code code} 為根層的拒收碼，{@code detail} 逐字）
 */
public record SiValidation(boolean ok, String row, long rowBytes, Long rowMaxBytes, List<Finding> findings) {

    public SiValidation {
        findings = findings == null ? List.of() : List.copyOf(findings);
    }

    /** 一筆不合的原因。 */
    public record Finding(String code, String detail) {
    }
}
