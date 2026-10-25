package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.si.SiConsoleWrite;

import java.util.UUID;

/**
 * Console 自己的稽核列的<b>寫入埠</b>（{@code console.si_console_writes}；TCS-SelfImprovingDecide-P2b W11、W13）：只有兩個動作——
 * 呼叫 Bridge 前先 {@link #insert}、確定未落檔時 {@link #deleteByAuditRef 補償刪除}。列不可改（資料庫觸發器），所以這裡沒有 update；
 * 唯一的 UPDATE（{@code subject_id} 由 NULL 填值）住在對帳讀面的 {@link SiConsoleWriteQueries#fillSubjectId}。
 * 呼叫者只有 {@code SiConsoleWriteService}（ArchUnit 鎖住）。
 */
public interface SiConsoleWriteRepository {

    /** 新增一列（獨立提交：必須在呼叫 Bridge 之前就已可見）；{@code audit_ref} 重複丟 {@code DataIntegrityViolationException}。 */
    void insert(SiConsoleWrite row);

    /** 補償：確定沒有落檔時刪掉這一列；回是否真的刪到（已不存在＝false）。 */
    boolean deleteByAuditRef(UUID auditRef);
}
