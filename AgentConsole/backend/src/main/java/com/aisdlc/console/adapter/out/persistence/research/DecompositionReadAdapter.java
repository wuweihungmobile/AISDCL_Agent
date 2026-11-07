package com.aisdlc.console.adapter.out.persistence.research;

import com.aisdlc.console.application.port.out.ResearchDecompositionReadPort;
import com.aisdlc.console.domain.model.research.ResearchRouteViews.Decomposition;
import com.aisdlc.console.domain.model.research.ResearchRouteViews.ImportRef;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * 拆解與 TASK_DECOMPOSITION 產物的 JDBC <b>唯讀</b>實作（{@link ResearchDecompositionReadPort}；ADR-003 D4）。「有效」的判準（D-120）：已簽核且仍符合凍結摘要的最新一筆，
 * 否則最新一筆。{@code content} 取該研究專案最新版 TASK_DECOMPOSITION 產物的 JSON 全文（Bridge 於拆解與簽核各寫一個新版本）。
 */
@Component
class DecompositionReadAdapter implements ResearchDecompositionReadPort {

    private static final String COLUMNS = "select id, path, draft_id, import_record_id, tcs_rel_path, tcs_sha256, prd_sha256, tasks_count, gate_rejection, "
            + "status, created_by, created_at from console.research_decompositions where research_id = :id";
    private static final String PRD_BASELINE_KEY = "01_specs/PRD-v1.0.0.md";

    private final JdbcClient jdbc;

    DecompositionReadAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Optional<Decomposition> effective(UUID researchId) {
        Optional<String> frozen = frozenPrdSha256(researchId);
        if (frozen.isPresent()) {
            Optional<Decomposition> valid = jdbc.sql(COLUMNS + " and status in ('SIGNED_OFF', 'FROZEN', 'IMPORTED') and prd_sha256 = :sha "
                    + "order by created_at desc, id limit 1").param("id", researchId).param("sha", frozen.get())
                    .query(DecompositionReadAdapter::row).optional();
            if (valid.isPresent()) {
                return valid.map(d -> withContent(researchId, d));
            }
        }
        return jdbc.sql(COLUMNS + " order by created_at desc, id limit 1").param("id", researchId).query(DecompositionReadAdapter::row).optional()
                .map(d -> withContent(researchId, d));
    }

    @Override
    public Optional<Decomposition> find(UUID researchId, UUID decompositionId) {
        return jdbc.sql(COLUMNS + " and id = :decomposition").param("id", researchId).param("decomposition", decompositionId)
                .query(DecompositionReadAdapter::row).optional().map(d -> withContent(researchId, d));
    }

    @Override
    public Optional<ImportRef> importRecordOf(UUID consoleProjectId, UUID decompositionId) {
        return jdbc.sql("select id, status, signed_off from console.import_records where source_file_name = :name "
                + "and parse_options ->> 'targetProjectId' = :project order by created_at desc, id limit 1")
                .param("name", "research-decomposition:" + decompositionId).param("project", consoleProjectId.toString())
                .query((rs, n) -> new ImportRef(ResearchJdbc.uuid(rs, "id"), rs.getString("status"), rs.getBoolean("signed_off"))).optional();
    }

    @Override
    public Optional<String> frozenPrdSha256(UUID researchId) {
        return jdbc.sql("select frozen_digests::text as digests from console.research_gate_decisions where research_id = :id and gate = 'GATE0' "
                + "and decision = 'APPROVED' order by decided_at desc limit 1").param("id", researchId)
                .query((rs, n) -> ResearchJdbc.object(rs.getString("digests"))).optional()
                .map(digests -> digests.get(PRD_BASELINE_KEY)).map(Object::toString).map(v -> v.startsWith("sha256:") ? v.substring(7) : v);
    }

    private Decomposition withContent(UUID researchId, Decomposition d) {
        Map<String, Object> content = jdbc.sql("select content from console.research_artifacts where research_id = :id and kind = 'TASK_DECOMPOSITION' "
                + "order by version desc limit 1").param("id", researchId)
                .query((rs, n) -> ResearchJdbc.object(rs.getString("content"))).optional().orElse(null);
        return new Decomposition(d.id(), d.path(), d.draftId(), d.importRecordId(), d.tcsRelPath(), d.tcsSha256(), d.prdSha256(), d.tasksCount(),
                d.gateRejection(), d.status(), d.createdBy(), d.createdAt(), content);
    }

    private static Decomposition row(ResultSet rs, int row) throws SQLException {
        return new Decomposition(ResearchJdbc.uuid(rs, "id"), rs.getString("path"), rs.getString("draft_id"), ResearchJdbc.uuid(rs, "import_record_id"),
                rs.getString("tcs_rel_path"), rs.getString("tcs_sha256"), rs.getString("prd_sha256"), rs.getInt("tasks_count"),
                rs.getString("gate_rejection"), rs.getString("status"), rs.getString("created_by"), ResearchJdbc.ts(rs, "created_at"), null);
    }
}
