package com.aisdlc.console.adapter.out.persistence.research;

import com.aisdlc.console.application.port.out.ResearchScrReadPort;
import com.aisdlc.console.domain.model.research.ResearchRouteViews.Scr;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.UUID;

/** 規格變更請求的 JDBC <b>唯讀</b>實作（{@link ResearchScrReadPort}；ADR-003 D4）：沒有 JPA 實體、沒有任何寫入敘述。 */
@Component
class ScrReadAdapter implements ResearchScrReadPort {

    private final JdbcClient jdbc;

    ScrReadAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<Scr> list(UUID researchId) {
        return jdbc.sql("select id, scr_no, kind, source_kind, reason, reason_class, affected_sections, status, prd_from_version_no, prd_to_version_no, "
                + "successor_research_id, impl_fsm_actions::text as impl_fsm_actions, requested_by, requested_at, decided_by, decided_at "
                + "from console.research_scr where research_id = :id order by scr_no").param("id", researchId).query(ScrReadAdapter::scr).list();
    }

    @Override
    public boolean hasOpen(UUID researchId) {
        return jdbc.sql("select count(*) from console.research_scr where research_id = :id and status = 'OPEN'").param("id", researchId)
                .query((rs, n) -> rs.getLong(1)).single() > 0;
    }

    private static Scr scr(ResultSet rs, int row) throws SQLException {
        return new Scr(ResearchJdbc.uuid(rs, "id"), rs.getInt("scr_no"), rs.getString("kind"), rs.getString("source_kind"), rs.getString("reason"),
                rs.getString("reason_class"), ResearchJdbc.strings(rs, "affected_sections"), rs.getString("status"),
                ResearchJdbc.nullableInt(rs, "prd_from_version_no"), ResearchJdbc.nullableInt(rs, "prd_to_version_no"),
                ResearchJdbc.uuid(rs, "successor_research_id"), ResearchJdbc.list(rs.getString("impl_fsm_actions")), rs.getString("requested_by"),
                ResearchJdbc.ts(rs, "requested_at"), rs.getString("decided_by"), ResearchJdbc.ts(rs, "decided_at"));
    }
}
