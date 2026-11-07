package com.aisdlc.console.adapter.out.persistence.research;

import com.aisdlc.console.application.port.out.ResearchDeliveryReadPort;
import com.aisdlc.console.domain.model.research.ResearchP2Views.DeliveryRow;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** {@code research_deliveries} 與分流目標路徑的 JDBC <b>唯讀</b>實作。 */
@Component
class DeliveryReadAdapter implements ResearchDeliveryReadPort {

    private final JdbcClient jdbc;

    DeliveryReadAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<DeliveryRow> deliveries(UUID researchId) {
        return jdbc.sql("select kind, ref, commit_sha, url, rtm_report_ref, fsm_state_after, status, created_by, created_at, snapshot_sha256 "
                + "from console.research_deliveries where research_id = :id order by created_at, id")
                .param("id", researchId)
                .query((rs, n) -> new DeliveryRow(rs.getString("kind"), rs.getString("ref"), rs.getString("commit_sha"), rs.getString("url"),
                        rs.getString("rtm_report_ref"), rs.getString("fsm_state_after"), rs.getString("status"), rs.getString("created_by"),
                        ResearchJdbc.ts(rs, "created_at"), rs.getString("snapshot_sha256")))
                .list();
    }

    @Override
    public Optional<String> projectRoot(UUID researchId) {
        return jdbc.sql("select target_path from console.research_route_decisions where research_id = :id order by created_at desc limit 1")
                .param("id", researchId).query((rs, n) -> rs.getString("target_path")).optional();
    }
}
