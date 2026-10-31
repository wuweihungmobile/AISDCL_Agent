package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.si.SiConsoleWrite;

import java.util.List;
import java.util.UUID;

/**
 * Console 自己的稽核列的<b>寫入埠</b>（{@code console.si_console_writes}；TCS-SelfImprovingDecide-P2b W11、W13；TCS-SelfImprovingDecideDedupe W-D1、W-D2）：
 * 兩個寫入動作——呼叫 Bridge 前先 {@link #insert}、確定未落檔時 {@link #deleteByAuditRef 補償刪除}——加決定重送閘用的唯讀查詢
 * {@link #findDecideAuditRefs}。列不可改（資料庫觸發器），所以這裡沒有 update；唯一的 UPDATE（{@code subject_id} 由 NULL 填值）住在對帳讀面的
 * {@link SiConsoleWriteQueries#fillSubjectId}。呼叫者只有 {@code SiConsoleWriteService}（ArchUnit 鎖住）。
 */
public interface SiConsoleWriteRepository {

    /** 新增一列（獨立提交：必須在呼叫 Bridge 之前就已可見）；{@code audit_ref} 重複丟 {@code DataIntegrityViolationException}。 */
    void insert(SiConsoleWrite row);

    /** 補償：確定沒有落檔時刪掉這一列；回是否真的刪到（已不存在＝false）。 */
    boolean deleteByAuditRef(UUID auditRef);

    /**
     * 重送閘的查詢（唯讀）：{@code kind='decide'} 且 {@code subject_id}、{@code digest} 與 dkind（取自 {@code body} 內的 {@code dkind} 鍵，不是欄位）三者
     * 都等於參數的列的 {@code audit_ref}，依 {@code time} 升冪、同刻依 {@code audit_ref} 升冪（小寫 UUID 字串的字典序，等同 PostgreSQL uuid 的位元組序；
     * 不是 {@link UUID#compareTo} 的有號比較，也不得在 Java 端重排）。{@code subject}、{@code digest} 或 {@code dkind} 為 {@code null} 回空清單：
     * 沒有卡面 digest 的動詞（rollback、unblock、resume）不受重送閘，所以不提供 null 比對。
     */
    List<UUID> findDecideAuditRefs(String subject, String digest, String dkind);
}
