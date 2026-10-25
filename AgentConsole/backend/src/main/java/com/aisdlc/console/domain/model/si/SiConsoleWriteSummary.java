package com.aisdlc.console.domain.model.si;

import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * 對帳讀面的稽核列投影（TCS-SelfImprovingDecide-P2b W14）：<b>沒有 {@code body} 與 {@code mac}</b>——讀面永遠不把簽章材料交出去，
 * 查詢本身就不選那兩欄。
 */
public record SiConsoleWriteSummary(UUID auditRef, SiWriteKind kind, String user, String role, OffsetDateTime time,
                                    String subjectId, String digest, String keyId) {
}
