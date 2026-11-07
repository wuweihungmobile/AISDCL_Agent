package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.research.ResearchRouteViews.Scr;

import java.util.List;
import java.util.UUID;

/** 規格變更請求（{@code research_scr}）的<b>唯讀</b>埠（ADR-003 D4）。實作只用 JdbcClient，不得出現寫入敘述（ArchUnit 字串掃描）。 */
public interface ResearchScrReadPort {

    /** 全部 SCR，依 scr_no 遞增。 */
    List<Scr> list(UUID researchId);

    /** 是否有 {@code OPEN} 的 SCR（D-102 前置守衛的第一道：內環唯讀）。 */
    boolean hasOpen(UUID researchId);
}
