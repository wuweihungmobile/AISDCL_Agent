package com.aisdlc.console.adapter.out.persistence.research;

import com.aisdlc.console.application.port.out.ResearchReviewReadPort;
import com.aisdlc.console.domain.model.research.ResearchViews.Defect;
import com.aisdlc.console.domain.model.research.ResearchViews.PrdVersion;
import com.aisdlc.console.domain.model.research.ResearchViews.PrecheckCheck;
import com.aisdlc.console.domain.model.research.ResearchViews.Round;
import com.aisdlc.console.domain.model.research.ResearchViews.Score;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * PRD 版本與審查輪的 JDBC <b>唯讀</b>實作（{@link ResearchReviewReadPort}）。審查輪列只在輪有結果時、與四維分數列、缺陷列同一交易一次寫入（D-57），所以這裡
 * 取到的每一列都是已完成評估的輪（沒有 status 欄、沒有進行中的輪）；{@code prdVersion}（semver）與缺陷的 {@code resolvedIn}（修正所在版本的 semver）以 join 取自
 * {@code research_prd_versions}。
 */
@Component
class ResearchReviewReadAdapter implements ResearchReviewReadPort {

    private static final String VERSION_COLUMNS = "select version_no, semver, kind, author_kind, author, parent_version_no, sha256, bytes, evidence_refs, "
            + "change_summary, created_at";

    private static final String ROUND_SELECT = "select r.id, r.round_no, r.fsm_generation, r.prd_version_no, v.semver as prd_version, r.trigger_kind, "
            + "r.precheck_passed, r.precheck_detail::text as precheck_detail, r.weighted_score, r.threshold, r.floor_score, r.min_dimension_score, "
            + "r.open_p1_count, r.passed, r.verdict, r.fsm_gate_result, r.fsm_retry_count, r.escalated, r.started_at, r.finished_at "
            + "from console.research_review_rounds r join console.research_prd_versions v "
            + "on v.research_id = r.research_id and v.version_no = r.prd_version_no where r.research_id = :id";

    private final JdbcClient jdbc;

    ResearchReviewReadAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<PrdVersion> prdVersions(UUID researchId) {
        return jdbc.sql(VERSION_COLUMNS + " from console.research_prd_versions where research_id = :id order by version_no")
                .param("id", researchId).query((rs, n) -> version(rs, null)).list();
    }

    @Override
    public Optional<PrdVersion> prdVersion(UUID researchId, int versionNo) {
        return jdbc.sql(VERSION_COLUMNS + ", content from console.research_prd_versions where research_id = :id and version_no = :no")
                .param("id", researchId).param("no", versionNo).query((rs, n) -> version(rs, rs.getString("content"))).optional();
    }

    @Override
    public List<Round> rounds(UUID researchId) {
        return withChildren(jdbc.sql(ROUND_SELECT + " order by r.round_no").param("id", researchId)
                .query(ResearchReviewReadAdapter::round).list());
    }

    @Override
    public Optional<Round> round(UUID researchId, int roundNo) {
        List<RoundRow> rows = jdbc.sql(ROUND_SELECT + " and r.round_no = :no").param("id", researchId).param("no", roundNo)
                .query(ResearchReviewReadAdapter::round).list();
        return withChildren(rows).stream().findFirst();
    }

    /** 一次取回這些輪的分數與缺陷（兩個查詢，不逐輪各查一次），組回完整的輪。 */
    private List<Round> withChildren(List<RoundRow> rows) {
        if (rows.isEmpty()) {
            return List.of();
        }
        List<UUID> ids = rows.stream().map(RoundRow::id).toList();
        Map<UUID, List<Score>> scores = new LinkedHashMap<>();
        jdbc.sql("select round_id, dimension, weight, score, agent_id, assist_agent_id, assist_agent_yaml_sha256, agent_yaml_sha256, persona_sha256, "
                + "summary from console.research_review_scores where round_id in (:ids) order by round_id, "
                + "case dimension when 'ARCHITECTURE' then 1 when 'PRODUCT' then 2 when 'QA' then 3 else 4 end")
                .param("ids", ids).query((rs, n) -> {
                    scores.computeIfAbsent(ResearchJdbc.uuid(rs, "round_id"), k -> new ArrayList<>())
                            .add(new Score(rs.getString("dimension"), rs.getBigDecimal("weight"), rs.getInt("score"), rs.getString("agent_id"),
                                    rs.getString("assist_agent_id"), rs.getString("assist_agent_yaml_sha256"), rs.getString("agent_yaml_sha256"),
                                    rs.getString("persona_sha256"), rs.getString("summary")));
                    return n;
                }).list();
        Map<UUID, List<Defect>> defects = new LinkedHashMap<>();
        jdbc.sql("select d.round_id, d.defect_no, d.dimension, d.severity, d.code, d.prd_anchor, d.description, d.suggestion, d.evidence_refs, d.status, "
                + "d.fixed_in_version_no, fv.semver as resolved_in, d.waived_by, d.waiver_reason, d.resolved_at "
                + "from console.research_review_defects d join console.research_review_rounds rr on rr.id = d.round_id "
                + "left join console.research_prd_versions fv on fv.research_id = rr.research_id and fv.version_no = d.fixed_in_version_no "
                + "where d.round_id in (:ids) order by d.round_id, d.defect_no")
                .param("ids", ids).query((rs, n) -> {
                    defects.computeIfAbsent(ResearchJdbc.uuid(rs, "round_id"), k -> new ArrayList<>())
                            .add(new Defect(rs.getString("defect_no"), rs.getString("dimension"), rs.getString("severity"), rs.getString("code"),
                                    rs.getString("prd_anchor"), rs.getString("description"), rs.getString("suggestion"),
                                    ResearchJdbc.strings(rs, "evidence_refs"), rs.getString("status"),
                                    ResearchJdbc.nullableInt(rs, "fixed_in_version_no"), rs.getString("resolved_in"), rs.getString("waived_by"),
                                    rs.getString("waiver_reason"), ResearchJdbc.ts(rs, "resolved_at")));
                    return n;
                }).list();
        return rows.stream().map(row -> row.complete(List.copyOf(scores.getOrDefault(row.id(), List.of())),
                List.copyOf(defects.getOrDefault(row.id(), List.of())))).toList();
    }

    private static PrdVersion version(ResultSet rs, String content) throws SQLException {
        return new PrdVersion(rs.getInt("version_no"), rs.getString("semver"), rs.getString("kind"), rs.getString("author_kind"),
                rs.getString("author"), ResearchJdbc.nullableInt(rs, "parent_version_no"), rs.getString("sha256"), rs.getInt("bytes"),
                ResearchJdbc.strings(rs, "evidence_refs"), rs.getString("change_summary"), ResearchJdbc.ts(rs, "created_at"), content);
    }

    private static RoundRow round(ResultSet rs, int row) throws SQLException {
        Object checks = ResearchJdbc.object(rs.getString("precheck_detail")).get("checks");
        List<PrecheckCheck> precheck = new ArrayList<>();
        if (checks instanceof List<?> list) {
            for (Object item : list) {
                if (item instanceof Map<?, ?> check) {
                    precheck.add(new PrecheckCheck(String.valueOf(check.get("id")), Boolean.TRUE.equals(check.get("passed")),
                            check.get("detail") == null ? "" : check.get("detail").toString()));
                }
            }
        }
        return new RoundRow(ResearchJdbc.uuid(rs, "id"), rs.getInt("round_no"), rs.getInt("fsm_generation"), rs.getInt("prd_version_no"),
                rs.getString("prd_version"), rs.getString("trigger_kind"), rs.getBoolean("precheck_passed"), List.copyOf(precheck),
                rs.getBigDecimal("weighted_score"), rs.getBigDecimal("threshold"), rs.getInt("floor_score"),
                ResearchJdbc.nullableInt(rs, "min_dimension_score"), rs.getInt("open_p1_count"), rs.getBoolean("passed"), rs.getString("verdict"),
                rs.getString("fsm_gate_result"), ResearchJdbc.nullableInt(rs, "fsm_retry_count"), rs.getBoolean("escalated"),
                ResearchJdbc.ts(rs, "started_at"), ResearchJdbc.ts(rs, "finished_at"));
    }

    /** 輪列本身（還沒有分數與缺陷）；{@link #complete} 補上兩者成為 {@link Round}。 */
    private record RoundRow(UUID id, int roundNo, int fsmGeneration, int prdVersionNo, String prdVersion, String triggerKind,
                            boolean precheckPassed, List<PrecheckCheck> precheckChecks, java.math.BigDecimal weightedScore,
                            java.math.BigDecimal threshold, int floorScore, Integer minDimensionScore, int openP1Count, boolean passed,
                            String verdict, String fsmGateResult, Integer fsmRetryCount, boolean escalated,
                            java.time.OffsetDateTime startedAt, java.time.OffsetDateTime finishedAt) {

        Round complete(List<Score> scores, List<Defect> defects) {
            return new Round(roundNo, fsmGeneration, prdVersionNo, prdVersion, triggerKind, precheckPassed, precheckChecks, weightedScore,
                    threshold, floorScore, minDimensionScore, openP1Count, passed, verdict, fsmGateResult, fsmRetryCount, escalated, scores,
                    defects, startedAt, finishedAt);
        }
    }
}
