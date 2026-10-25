package com.aisdlc.console.domain.model.si;

/**
 * Bridge 對稽核檔落地的 201 回應（{@code {"audit_ref": …, "stored": true}}；TCS-SelfImprovingDecide-P2b W3）。
 *
 * @param auditRef Bridge 回報已落檔的稽核編號
 * @param stored   檔案已落地
 */
public record SiWriteAck(String auditRef, boolean stored) {
}
