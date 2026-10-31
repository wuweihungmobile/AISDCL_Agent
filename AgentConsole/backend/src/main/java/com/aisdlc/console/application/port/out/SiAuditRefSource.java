package com.aisdlc.console.application.port.out;

/**
 * 稽核編號（{@code audit_ref}）的來源（TCS-SelfImprovingDecide-P2b W11）：預設每次取一個新的 {@code UUID.randomUUID()}
 * （<b>小寫正規 UUID</b>）；測試以佇列式的實作固定序列（黃金檔的 ref 固定）。<b>通過全部閘門的</b>請求恰取一次、重送一律新 ref
 * （同 ref 會被根層 CLI 以 AUDIT-REF-REUSED 拒收）；授權失敗、寫入面停用、輸入閘未通過，或決定被重送閘擋下（409 {@code si_decision_duplicate}；
 * TCS-SelfImprovingDecideDedupe W-D1）時一次都不取。
 */
public interface SiAuditRefSource {

    /** 下一個稽核編號：小寫正規 UUID 字串。 */
    String next();
}
