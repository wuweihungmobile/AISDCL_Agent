package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.si.SiConsoleWriteSummary;

import java.util.Collection;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Console 自己的稽核列的<b>對帳讀埠</b>（TCS-SelfImprovingDecide-P2b W14）：唯讀查詢加唯一的回填。查詢一律不選 {@code body} 與
 * {@code mac}（簽章材料不離開寫入路徑）；呼叫者只有 {@code SiReconcileService}。
 */
public interface SiConsoleWriteQueries {

    /** 時間新到舊（同刻依 {@code audit_ref} 升冪）的前 {@code limit} 列。 */
    List<SiConsoleWriteSummary> findRecent(int limit);

    /** 候選編號中，表內真的有列的那些（帳本有而表內沒有的＝orphan 由差集得出）。 */
    Set<UUID> findExistingAuditRefs(Collection<UUID> candidates);

    /** 還沒有 {@code subject_id} 的 obs-add 列（等入帳後由帳本的新列號回填）。 */
    Set<UUID> findObsAddRefsWithoutSubject();

    /**
     * 回填：{@code UPDATE … SET subject_id = ? WHERE audit_ref = ? AND subject_id IS NULL AND kind = 'obs-add'}（冪等；
     * 已有值的列不動）。回影響的列數（0 或 1）。這是對帳讀路徑<b>唯一</b>的副作用，也是本表唯一的 UPDATE。
     */
    int fillSubjectId(UUID auditRef, String subjectId);
}
