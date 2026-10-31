package com.aisdlc.console.domain.model.si;

import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * 對帳讀面的稽核列投影（TCS-SelfImprovingDecide-P2b W14；TCS-SelfImprovingDecideDedupe W-D2）：<b>沒有整欄 {@code body} 與 {@code mac}</b>——讀面永遠不把
 * 簽章材料交出去，查詢本身就不選那兩欄；{@code dkind} 是查詢以表達式從 {@code body} 取出的決定動詞（只有 {@code kind=decide} 的列有值；
 * 其餘 kind 與 body 沒有 {@code dkind} 鍵的列為 {@code null}）。
 */
public record SiConsoleWriteSummary(UUID auditRef, SiWriteKind kind, String dkind, String user, String role, OffsetDateTime time,
                                    String subjectId, String digest, String keyId) {
}
