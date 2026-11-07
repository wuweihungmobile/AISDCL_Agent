package com.aisdlc.console.application.port.in;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Caller;
import com.aisdlc.console.domain.model.research.ResearchRouteViews.Scr;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 規格變更請求用例（API-RP-15；PRD FR-R2P-19；ADR-XPLAT-017 D5）：發起（OPERATOR 以上；先停進行中的 run、再呼 Bridge {@code :scr}）、清單（VIEWER 以上、JDBC 唯讀）、
 * MINOR 套用重試（僅 ADMIN；Bridge {@code :scr-apply}）。console-api 對研究表零寫入。
 */
public interface ResearchScrUseCase {

    /** 發起請求（欄位可為 null＝請求沒給；{@code reasonClass} 為中文五分類或其 DB 碼）。 */
    record ScrInput(String kind, String sourceKind, String reason, String reasonClass, List<String> affectedSections) {
    }

    /** 發起：回 Bridge 的本文（snake_case；MINOR 與 MAJOR 為 202 形態、HEALING_FAILED 帶 {@code recovery}）。 */
    Map<String, Object> open(Caller caller, UUID researchId, ScrInput input);

    List<Scr> list(UUID researchId);

    /** MINOR 套用重試：回 Bridge 的本文（snake_case）。 */
    Map<String, Object> apply(Caller caller, UUID researchId, int scrNo);
}
