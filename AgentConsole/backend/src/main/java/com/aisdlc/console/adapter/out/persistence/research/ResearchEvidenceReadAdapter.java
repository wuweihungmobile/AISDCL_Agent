package com.aisdlc.console.adapter.out.persistence.research;

import com.aisdlc.console.application.port.out.ResearchEvidenceReadPort;
import com.aisdlc.console.domain.model.research.ResearchViews.EvidenceItem;
import com.aisdlc.console.domain.model.research.ResearchViews.Fetch;
import com.aisdlc.console.domain.model.research.ResearchViews.Matrix;
import com.aisdlc.console.domain.model.research.ResearchViews.Source;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.sql.Date;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * 來源與證據矩陣的 JDBC <b>唯讀</b>實作（{@link ResearchEvidenceReadPort}）。矩陣版本＝{@code research_artifacts(kind='EVIDENCE_ITEMS').version}＝證據列的
 * {@code matrix_version}；反證、誠實劃界與搜尋紀錄隨 {@code EVIDENCE_ITEMS} 產物的 {@code content} 全文保存（D-43，P0 不另立表），這裡原樣取出、由 DTO 層解析。
 */
@Component
class ResearchEvidenceReadAdapter implements ResearchEvidenceReadPort {

    private final JdbcClient jdbc;

    ResearchEvidenceReadAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<Source> sources(UUID researchId) {
        Map<UUID, Source> bySource = new LinkedHashMap<>();
        Map<UUID, List<Fetch>> fetches = new LinkedHashMap<>();
        jdbc.sql("select source_id, fetch_no, fetch_method, observed_by, host, http_status, outcome, raw_sha256, raw_bytes, fetched_at "
                + "from console.research_fetches where research_id = :id and source_id is not null order by fetched_at, fetch_no")
                .param("id", researchId)
                .query((rs, n) -> {
                    fetches.computeIfAbsent(ResearchJdbc.uuid(rs, "source_id"), k -> new ArrayList<>()).add(fetch(rs));
                    return n;
                }).list();
        jdbc.sql("select id, source_no, layer, tier, verification, anchor_kind, url, doi, git_commit, title, authors_org, published_at, "
                + "source_type, license_spdx, license_note, clue_only from console.research_sources where research_id = :id order by source_no")
                .param("id", researchId)
                .query((rs, n) -> {
                    UUID id = ResearchJdbc.uuid(rs, "id");
                    Date published = rs.getDate("published_at");
                    bySource.put(id, new Source(rs.getString("source_no"), rs.getString("layer"), rs.getString("tier"),
                            rs.getString("verification"), rs.getString("anchor_kind"), rs.getString("url"), rs.getString("doi"),
                            rs.getString("git_commit"), rs.getString("title"), rs.getString("authors_org"),
                            published == null ? null : published.toLocalDate(), rs.getString("source_type"),
                            rs.getString("license_spdx"), rs.getString("license_note"), rs.getBoolean("clue_only"),
                            List.copyOf(fetches.getOrDefault(id, List.of()))));
                    return n;
                }).list();
        return List.copyOf(bySource.values());
    }

    @Override
    public Optional<Matrix> matrix(UUID researchId, Integer matrixVersion) {
        Integer version = matrixVersion != null ? matrixVersion : jdbc.sql("select coalesce("
                + "(select max(version) from console.research_artifacts where research_id = :id and kind = 'EVIDENCE_ITEMS'), "
                + "(select max(matrix_version) from console.research_evidence_items where research_id = :id))")
                .param("id", researchId).query((rs, n) -> ResearchJdbc.nullableInt(rs, 1)).optional().orElse(null);   // 尚無證據時是 NULL；single() 會丟例外
        if (version == null) {
            return Optional.empty();
        }
        List<EvidenceItem> items = jdbc.sql("select e.evidence_no, s.source_no, e.candidate, e.claim, e.f1_mechanism, e.f2_evidence, e.f3_critique, "
                + "e.f4_risk_tags, e.f5_applicability::text as f5_applicability, e.f6_limits, e.f7_verification, e.strength, e.unanchored, "
                + "e.matrix_version, e.scope_rev from console.research_evidence_items e join console.research_sources s on s.id = e.source_id "
                + "where e.research_id = :id and e.matrix_version = :version order by e.evidence_no")
                .param("id", researchId).param("version", version).query(ResearchEvidenceReadAdapter::item).list();
        String sha256 = jdbc.sql("select sha256 from console.research_artifacts where research_id = :id and version = :version "
                + "and kind in ('EVIDENCE_MATRIX', 'EVIDENCE_ITEMS') order by (kind = 'EVIDENCE_MATRIX') desc limit 1")
                .param("id", researchId).param("version", version).query((rs, n) -> rs.getString(1)).optional().orElse("");
        String itemsJson = jdbc.sql("select content from console.research_artifacts where research_id = :id and version = :version "
                + "and kind = 'EVIDENCE_ITEMS'").param("id", researchId).param("version", version)
                .query((rs, n) -> rs.getString(1)).optional().orElse(null);
        if (items.isEmpty() && sha256.isEmpty() && itemsJson == null) {
            return Optional.empty();
        }
        int scopeRev = items.isEmpty() ? 1 : items.stream().mapToInt(EvidenceItem::scopeRev).max().orElse(1);
        return Optional.of(new Matrix(version, scopeRev, sha256, items, itemsJson));
    }

    private static Fetch fetch(ResultSet rs) throws SQLException {
        return new Fetch(rs.getString("fetch_no"), rs.getString("fetch_method"), rs.getString("observed_by"), rs.getString("host"),
                ResearchJdbc.nullableInt(rs, "http_status"), rs.getString("outcome"), rs.getString("raw_sha256"),
                ResearchJdbc.nullableLong(rs, "raw_bytes"), ResearchJdbc.ts(rs, "fetched_at"));
    }

    private static EvidenceItem item(ResultSet rs, int row) throws SQLException {
        return new EvidenceItem(rs.getString("evidence_no"), rs.getString("source_no"), rs.getString("candidate"), rs.getString("claim"),
                rs.getString("f1_mechanism"), rs.getString("f2_evidence"), rs.getString("f3_critique"),
                ResearchJdbc.strings(rs, "f4_risk_tags"), ResearchJdbc.object(rs.getString("f5_applicability")), rs.getString("f6_limits"),
                rs.getString("f7_verification"), rs.getString("strength"), rs.getBoolean("unanchored"), rs.getInt("matrix_version"),
                rs.getInt("scope_rev"));
    }
}
