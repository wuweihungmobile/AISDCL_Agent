package com.aisdlc.console.domain.model.si;

import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * Console 自己的稽核列（{@code console.si_console_writes}；TCS-SelfImprovingDecide-P2b W11、W13）：每次經 Bridge 落稽核檔的寫入，
 * 在呼叫 Bridge <b>之前</b>先寫一列同型的列——寧可有列無檔、不要有檔無列（PRD §9.3）。列不可改（資料庫觸發器），唯一例外是
 * obs-add 的 {@code subjectId} 由 {@code null} 填值（對帳讀面回填）。
 *
 * @param time      稽核 body 的 {@code time}（秒精度）
 * @param subjectId decide＝PROP 號（resume 為 RUN 號）、obs-close＝OBS 號、obs-add＝{@code null}（入帳後才知道新列號）
 * @param digest    只有帶卡面 digest 的六種動詞才有
 * @param body      稽核 body 字串（<b>簽章的對象</b>，逐字）
 * @param keyId     簽章金鑰的 sha256 前 8 碼
 * @param mac       HMAC-SHA256 小寫十六進位（64 碼）
 */
public record SiConsoleWrite(UUID auditRef, SiWriteKind kind, String user, String role, OffsetDateTime time,
                             String subjectId, String digest, String body, String keyId, String mac) {

    /** 🔴 {@code body} 與 {@code mac} 不進 {@code toString}（日誌）：只留辨識用的欄位。 */
    @Override
    public String toString() {
        return "SiConsoleWrite[auditRef=" + auditRef + ", kind=" + kind.wire() + ", user=" + user + ", time=" + time
                + ", subjectId=" + subjectId + ", keyId=" + keyId + "]";
    }
}
