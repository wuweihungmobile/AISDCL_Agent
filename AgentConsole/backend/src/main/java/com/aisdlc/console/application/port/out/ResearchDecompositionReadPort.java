package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.research.ResearchRouteViews.Decomposition;
import com.aisdlc.console.domain.model.research.ResearchRouteViews.ImportRef;

import java.util.Optional;
import java.util.UUID;

/** 拆解（{@code research_decompositions}、{@code research_artifacts(kind=TASK_DECOMPOSITION)}）的<b>唯讀</b>埠（ADR-003 D4）。實作只用 JdbcClient，不得出現寫入敘述。 */
public interface ResearchDecompositionReadPort {

    /**
     * 有效拆解（D-120）：已簽核（{@code SIGNED_OFF}／{@code FROZEN}／{@code IMPORTED}）且仍符合凍結摘要的最新一筆；沒有符合者退回「最新一筆」（任何狀態，
     * 含 DRAFTED、STALE）；完全沒有拆解為 empty。{@code content} 取該研究專案最新版 TASK_DECOMPOSITION artifact 的 JSON 全文。
     */
    Optional<Decomposition> effective(UUID researchId);

    /** 以 id 取單筆（限該研究專案；{@code content} 同上）。 */
    Optional<Decomposition> find(UUID researchId, UUID decompositionId);

    /**
     * 同一 Console 專案、同一拆解的既有匯入記錄（簽核冪等，D-133）：以 {@code import_records.source_file_name＝research-decomposition:<拆解 id>} 與
     * {@code parse_options.targetProjectId} 查（既有欄位，不加 DDL）；有多筆取最新一筆；沒有為 empty。
     */
    Optional<ImportRef> importRecordOf(UUID consoleProjectId, UUID decompositionId);

    /** 目前 Gate 0（或 SCR 版 Gate 0）凍結的 PRD 基線 sha256（小寫十六進位、已去 {@code sha256:} 前綴）；沒有核准決定為 empty。 */
    Optional<String> frozenPrdSha256(UUID researchId);
}
