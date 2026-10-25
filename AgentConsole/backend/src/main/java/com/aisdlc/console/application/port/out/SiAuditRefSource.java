package com.aisdlc.console.application.port.out;

/**
 * 稽核編號（{@code audit_ref}）的來源（TCS-SelfImprovingDecide-P2b W11）：預設每次取一個新的 {@code UUID.randomUUID()}
 * （<b>小寫正規 UUID</b>）；測試以佇列式的實作固定序列（黃金檔的 ref 固定）。一個請求恰取一次、重送一律新 ref
 * （同 ref 會被根層 CLI 以 AUDIT-REF-REUSED 拒收）；輸入閘未通過、授權失敗或寫入面停用時一次都不取。
 */
public interface SiAuditRefSource {

    /** 下一個稽核編號：小寫正規 UUID 字串。 */
    String next();
}
