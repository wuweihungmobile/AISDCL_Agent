package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.research.ResearchRouteViews.Route;

import java.util.Optional;
import java.util.UUID;

/**
 * 分流（{@code research_route_decisions}、{@code research_route_steps}）的<b>唯讀</b>埠（ADR-003 D4：console-api 對研究表零寫入，Bridge 是唯一寫入者）。
 * 實作住 {@code adapter.out.persistence.research}，只用 {@code JdbcClient}、沒有 JPA 實體，原始碼不得出現 INSERT／UPDATE／DELETE（ArchUnit 字串掃描）。
 */
public interface ResearchRouteReadPort {

    /** 該研究專案最新的一筆分流（含步驟；依 created_at 新到舊取第一筆）；沒有分流為 empty。 */
    Optional<Route> latest(UUID researchId);

    /** 佔住 {@code ux_research_route_active} 的有效分流（PENDING、RUNNING 或 SUCCEEDED；至多一筆）；沒有為 empty。 */
    Optional<Route> active(UUID researchId);
}
