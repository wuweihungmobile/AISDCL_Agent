package com.aisdlc.console.adapter.out.persistence.research;

import com.aisdlc.console.application.port.out.ResearchProjectReadPort;
import com.aisdlc.console.domain.model.research.ResearchViews.Counts;
import com.aisdlc.console.domain.model.research.ResearchViews.Event;
import com.aisdlc.console.domain.model.research.ResearchViews.EventPage;
import com.aisdlc.console.domain.model.research.ResearchViews.LastReview;
import com.aisdlc.console.domain.model.research.ResearchViews.Project;
import com.aisdlc.console.domain.model.research.ResearchViews.RecordClass;
import com.aisdlc.console.domain.model.research.ResearchViews.RunFact;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Optional;
import java.util.OptionalLong;
import java.util.UUID;

/**
 * 研究專案、事件帳與記錄完整率的 JDBC <b>唯讀</b>實作（{@link ResearchProjectReadPort}；ADR-003 D4）。沒有 JPA 實體、沒有任何寫入敘述：{@code console.research_*} 只有
 * Bridge 能寫，console-api 只讀（原始碼掃描與 ArchUnit 鎖住，AT-960-4-E-1）。時間欄位一律 {@code timestamptz}、以 {@code OffsetDateTime} 取回。
 */
@Component
class ResearchProjectReadAdapter implements ResearchProjectReadPort {

    private static final String PROJECT_COLUMNS = "select id, rp_no, slug, title, topic, scope::text as scope, scope_rev, depth_level, target_scope, "
            + "fsm_project, fsm_generation, flow_step, flow_phase, flow_status, flow_detail, console_project_id, parent_research_id, "
            + "last_event_seq, created_by, created_at, updated_at, archived_at, workspace_path from console.research_projects";

    private static final String EVENT_COLUMNS = "select seq, event_type, step, actor, ref_kind, ref_id, payload::text as payload, occurred_at "
            + "from console.research_events where research_id = :id and seq > :after order by seq limit :limit";

    /** PRD §5.1.8 的 14 類記錄的名稱（R7、R8、R10、R11、R12 對應 V19 的表與視圖；⚖P1-16 口徑見 {@link #recordClasses}）。 */
    private static final List<String> CLASS_NAMES = List.of("議題與範圍", "抓取紀錄", "證據矩陣版本", "PRD 版本", "審查輪", "Gate 0 決定",
            "分流決定與副作用步驟", "拆解結果", "stage run", "自癒嘗試", "交付", "SCR", "步驟歷史", "產物登記與對帳結果");

    private final JdbcClient jdbc;

    ResearchProjectReadAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<Project> findAll(boolean archived) {
        return jdbc.sql(PROJECT_COLUMNS + " where (archived_at is not null) = :archived order by updated_at desc, rp_no desc")
                .param("archived", archived).query(ResearchProjectReadAdapter::project).list();
    }

    @Override
    public Optional<Project> findById(UUID id) {
        return jdbc.sql(PROJECT_COLUMNS + " where id = :id").param("id", id).query(ResearchProjectReadAdapter::project).optional();
    }

    @Override
    public boolean exists(UUID id) {
        return jdbc.sql("select count(*) from console.research_projects where id = :id").param("id", id)
                .query((rs, n) -> rs.getLong(1)).single() > 0;
    }

    @Override
    public Counts counts(UUID id) {
        return jdbc.sql("select "
                + "(select count(*) from console.research_sources where research_id = :id) as sources, "
                + "(select count(*) from console.research_evidence_items where research_id = :id and matrix_version = "
                + "  (select max(matrix_version) from console.research_evidence_items where research_id = :id)) as evidence_items, "
                + "(select count(*) from console.research_prd_versions where research_id = :id) as prd_versions, "
                + "(select count(*) from console.research_review_rounds where research_id = :id) as review_rounds, "
                + "(select count(*) from console.research_review_defects d join console.research_review_rounds r on r.id = d.round_id "
                + "  where r.research_id = :id and d.status = 'OPEN') as open_defects")
                .param("id", id)
                .query((rs, n) -> new Counts(rs.getInt("sources"), rs.getInt("evidence_items"), rs.getInt("prd_versions"),
                        rs.getInt("review_rounds"), rs.getInt("open_defects")))
                .single();
    }

    @Override
    public Optional<LastReview> lastReview(UUID id) {
        return jdbc.sql("select round_no, weighted_score, min_dimension_score, passed, escalated from console.research_review_rounds "
                + "where research_id = :id order by round_no desc limit 1").param("id", id)
                .query((rs, n) -> new LastReview(rs.getInt("round_no"), rs.getBigDecimal("weighted_score"),
                        ResearchJdbc.nullableInt(rs, "min_dimension_score"), rs.getBoolean("passed"), rs.getBoolean("escalated")))
                .optional();
    }

    @Override
    public OptionalLong headPrdVersion(UUID id) {
        // 聚合在沒有列時仍回一列 NULL；single() 對 null 值丟 TypeMismatchDataAccessException（新專案詳情會 500），所以用 optional()：null＝尚無版本
        return jdbc.sql("select max(version_no) from console.research_prd_versions where research_id = :id").param("id", id)
                .query((rs, n) -> ResearchJdbc.nullableLong(rs, 1)).optional().map(OptionalLong::of).orElseGet(OptionalLong::empty);
    }

    @Override
    public EventPage events(UUID id, long afterSeq, int limit) {
        List<Event> rows = eventsAfter(id, afterSeq, limit + 1);
        boolean truncated = rows.size() > limit;
        List<Event> items = truncated ? rows.subList(0, limit) : rows;
        return new EventPage(List.copyOf(items), items.isEmpty() ? afterSeq : items.get(items.size() - 1).seq(), truncated);
    }

    @Override
    public List<Event> eventsAfter(UUID id, long afterSeq, int limit) {
        return jdbc.sql(EVENT_COLUMNS).param("id", id).param("after", afterSeq).param("limit", limit)
                .query(ResearchProjectReadAdapter::event).list();
    }

    @Override
    public long maxEventSeq(UUID id) {
        return jdbc.sql("select coalesce(max(seq), 0) from console.research_events where research_id = :id").param("id", id)
                .query((rs, n) -> rs.getLong(1)).single();
    }

    @Override
    public OptionalLong replayWindowStart(UUID id, int window) {
        // 同 headPrdVersion：沒有任何事件列時 min(seq) 是 NULL，用 optional() 而不是 single()
        return jdbc.sql("select min(seq) from (select seq from console.research_events where research_id = :id "
                + "order by seq desc limit :window) newest").param("id", id).param("window", window)
                .query((rs, n) -> ResearchJdbc.nullableLong(rs, 1)).optional().map(OptionalLong::of).orElseGet(OptionalLong::empty);
    }

    /**
     * R1～R14 各類的筆數。V19 口徑（⚖P1-16）：R7＝{@code research_route_decisions} 筆數、R8＝{@code research_decompositions}、R10＝視圖
     * {@code v_research_healing_attempts}（自癒嘗試，唯讀視圖）、R11＝{@code research_deliveries}（P2 寫入）、R12＝{@code research_scr}。
     */
    @Override
    public List<RecordClass> recordClasses(UUID id) {
        long[] counts = jdbc.sql("select "
                + "(select count(*) from console.research_projects where id = :id) as r1, "
                + "(select count(*) from console.research_fetches where research_id = :id) as r2, "
                + "(select count(*) from console.research_artifacts where research_id = :id and kind in ('EVIDENCE_ITEMS', 'EVIDENCE_MATRIX')) as r3, "
                + "(select count(*) from console.research_prd_versions where research_id = :id) as r4, "
                + "(select count(*) from console.research_review_rounds where research_id = :id) as r5, "
                + "(select count(*) from console.research_gate_decisions where research_id = :id and gate = 'GATE0') as r6, "
                + "(select count(*) from console.research_route_decisions where research_id = :id) as r7, "
                + "(select count(*) from console.research_decompositions where research_id = :id) as r8, "
                + "(select count(*) from console.research_stage_runs where research_id = :id) as r9, "
                + "(select count(*) from console.v_research_healing_attempts where research_id = :id) as r10, "
                + "(select count(*) from console.research_deliveries where research_id = :id) as r11, "
                + "(select count(*) from console.research_scr where research_id = :id) as r12, "
                + "(select count(*) from console.research_events where research_id = :id and event_type = 'research.step') as r13, "
                + "(select count(*) from console.research_artifacts where research_id = :id) as r14")
                .param("id", id)
                .query((rs, n) -> new long[] {rs.getLong("r1"), rs.getLong("r2"), rs.getLong("r3"), rs.getLong("r4"), rs.getLong("r5"),
                        rs.getLong("r6"), rs.getLong("r7"), rs.getLong("r8"), rs.getLong("r9"), rs.getLong("r10"), rs.getLong("r11"),
                        rs.getLong("r12"), rs.getLong("r13"), rs.getLong("r14")})
                .single();
        return java.util.stream.IntStream.range(0, CLASS_NAMES.size())
                .mapToObj(i -> new RecordClass("R" + (i + 1), CLASS_NAMES.get(i), (int) counts[i])).toList();
    }

    @Override
    public int humanReturnCount(UUID id, String fsmProject) {
        return jdbc.sql("select count(*) from console.research_gate_decisions where research_id = :id and gate = 'GATE0' "
                + "and decision = 'CHANGES' and fsm_project = :fsm").param("id", id).param("fsm", fsmProject)
                .query((rs, n) -> rs.getInt(1)).single();
    }

    @Override
    public Optional<UUID> researchIdOfConsoleProject(UUID consoleProjectId) {
        return jdbc.sql("select id from console.research_projects where console_project_id = :project order by created_at limit 1")
                .param("project", consoleProjectId).query((rs, n) -> ResearchJdbc.uuid(rs, "id")).optional();
    }

    @Override
    public Optional<RunFact> latestRun(UUID consoleProjectId) {
        return jdbc.sql("select r.status, "
                + "exists(select 1 from console.execution_steps s where s.run_id = r.id and s.status = 'RETRYING') as retrying, "
                + "exists(select 1 from console.review_requests q where q.run_id = r.id and q.status = 'PENDING') as pending "
                + "from console.execution_runs r where r.project_id = :project order by r.started_at desc nulls last, r.run_number desc limit 1")
                .param("project", consoleProjectId)
                .query((rs, n) -> new RunFact(rs.getString("status"), rs.getBoolean("retrying"), rs.getBoolean("pending")))
                .optional();
    }

    private static Project project(ResultSet rs, int row) throws SQLException {
        return new Project(ResearchJdbc.uuid(rs, "id"), rs.getString("rp_no"), rs.getString("slug"), rs.getString("title"),
                rs.getString("topic"), ResearchJdbc.object(rs.getString("scope")), rs.getInt("scope_rev"), rs.getString("depth_level"),
                rs.getString("target_scope"), rs.getString("fsm_project"), rs.getInt("fsm_generation"), rs.getString("flow_step"),
                rs.getString("flow_phase"), rs.getString("flow_status"), rs.getString("flow_detail"),
                ResearchJdbc.uuid(rs, "console_project_id"), ResearchJdbc.uuid(rs, "parent_research_id"), rs.getLong("last_event_seq"),
                rs.getString("created_by"), ResearchJdbc.ts(rs, "created_at"), ResearchJdbc.ts(rs, "updated_at"),
                ResearchJdbc.ts(rs, "archived_at"), rs.getString("workspace_path"));
    }

    private static Event event(ResultSet rs, int row) throws SQLException {
        return new Event(rs.getLong("seq"), rs.getString("event_type"), rs.getString("step"), rs.getString("actor"),
                rs.getString("ref_kind"), ResearchJdbc.uuid(rs, "ref_id"), ResearchJdbc.object(rs.getString("payload")),
                ResearchJdbc.ts(rs, "occurred_at"));
    }
}
