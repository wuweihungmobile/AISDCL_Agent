package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.research.ResearchP2Views.DeliveryRow;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** 交付列的<b>唯讀</b>埠（{@code research_deliveries}、分流決定的目標路徑）。 */
public interface ResearchDeliveryReadPort {

    /** 交付列，建立時間遞增。 */
    List<DeliveryRow> deliveries(UUID researchId);

    /** 最新一筆分流決定的 {@code target_path}（沒有＝empty）。 */
    Optional<String> projectRoot(UUID researchId);
}
